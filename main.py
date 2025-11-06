"""
FastAPI service for chatting with a database using natural language.

This service provides a REST API endpoint that accepts natural language queries,
translates them to SQL using OpenAI, executes them safely against a SQLite database,
and returns structured JSON responses.
"""

import logging
import sqlite3
import os
import re
import json
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
import pandas as pd
from io import StringIO

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from openai import OpenAI
from dotenv import load_dotenv

# Configure logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Chat with Database API",
    description="API for querying databases using natural language",
    version="1.0.0"
)

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DB_URL = os.getenv("DB_URL", "database.db")

# Initialize OpenAI client
openai_client = None
if OPENAI_API_KEY:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
    logger.info("OpenAI client initialized successfully")
else:
    logger.warning("OPENAI_API_KEY not found. Natural language to SQL translation will not work.")


# Pydantic models for request/response
class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    message: str = Field(..., description="Natural language query about the database")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Show me the last 10 users"
            }
        }


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""
    message: str = Field(..., description="Response message")
    sql_query: Optional[str] = Field(None, description="Generated SQL query")
    results: Optional[List[Dict[str, Any]]] = Field(None, description="Query results")
    row_count: Optional[int] = Field(None, description="Number of rows returned")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Found 10 users",
                "sql_query": "SELECT * FROM users LIMIT 10",
                "results": [{"id": 1, "name": "John"}],
                "row_count": 10
            }
        }


# Database utility functions
@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = None
    try:
        conn = sqlite3.connect(DB_URL)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        logger.info(f"Connected to database: {DB_URL}")
        yield conn
    except sqlite3.Error as e:
        logger.error(f"Database connection error: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if conn:
            conn.close()
            logger.info("Database connection closed")


def get_table_names(conn: sqlite3.Connection) -> List[str]:
    """Get all table names from the database"""
    try:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
        table_names = [row[0] for row in cursor.fetchall()]
        logger.info(f"Found {len(table_names)} tables: {table_names}")
        return table_names
    except sqlite3.Error as e:
        logger.error(f"Error fetching table names: {e}")
        return []


def get_column_names(conn: sqlite3.Connection, table_name: str) -> List[str]:
    """Get all column names for a specific table"""
    try:
        # Validate table name to prevent SQL injection
        if not re.match(r'^[a-zA-Z0-9_]+$', table_name):
            logger.error(f"Invalid table name: {table_name}")
            return []
        cursor = conn.execute(f"PRAGMA table_info('{table_name}');")
        column_names = [row[1] for row in cursor.fetchall()]
        logger.info(f"Table '{table_name}' has columns: {column_names}")
        return column_names
    except sqlite3.Error as e:
        logger.error(f"Error fetching column names for table '{table_name}': {e}")
        return []


def get_database_schema(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Get information about all tables and their columns in the database"""
    table_dicts = []
    for table_name in get_table_names(conn):
        column_names = get_column_names(conn, table_name)
        table_dicts.append({"table_name": table_name, "column_names": column_names})
    return table_dicts


def generate_sql_query(question: str, database_schema: str) -> str:
    """
    Generate SQL query from natural language using OpenAI.
    Falls back to a basic query if OpenAI is not available.
    """
    if not openai_client:
        logger.warning("OpenAI client not available. Using fallback query generation.")
        # Basic fallback - extract table name if mentioned
        return generate_fallback_query(question, database_schema)
    
    try:
        logger.info(f"Generating SQL query for question: {question}")
        
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "ask_database",
                    "description": "Use this function to answer a question about the database",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": f"""
                                    Write a SQL query to extract the necessary information to answer the user's question.
                                    The query should use the following database schema:
                                    {database_schema}
                                    Ensure that the SQL query is written in plain text and accurately reflects the schema provided.
                                """,
                            },
                        },
                        "required": ["query"],
                    },
                }
            }
        ]
        
        chat_completion = openai_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "Answer user questions by generating SQL queries",
                },
                {
                    "role": "user",
                    "content": question,
                }
            ],
            model="gpt-4o-mini",
            tools=tools
        )
        
        message = chat_completion.choices[0].message
        if message.tool_calls and len(message.tool_calls) > 0:
            # Safely parse JSON instead of using eval()
            arguments = json.loads(message.tool_calls[0].function.arguments)
            query = arguments['query']
            logger.info(f"Generated SQL query: {query}")
            return query
        else:
            logger.warning("No SQL query generated by OpenAI")
            return generate_fallback_query(question, database_schema)
            
    except Exception as e:
        logger.error(f"Error calling OpenAI API: {e}. Using fallback query generation.")
        return generate_fallback_query(question, database_schema)


def generate_fallback_query(question: str, database_schema: str) -> str:
    """
    Generate a basic SQL query when OpenAI is not available.
    This is a simple pattern-matching approach.
    """
    question_lower = question.lower()
    
    # Extract table names from schema
    table_matches = re.findall(r'Table: (\w+)', database_schema)
    
    if not table_matches:
        return "SELECT * FROM sqlite_master WHERE type='table';"
    
    # Try to find which table is mentioned in the question
    mentioned_table = None
    for table in table_matches:
        if table.lower() in question_lower:
            mentioned_table = table
            break
    
    # If no table mentioned, use the first table
    if not mentioned_table:
        mentioned_table = table_matches[0]
    
    # Check for LIMIT clause
    limit_match = re.search(r'(\d+)\s+(?:last|first|recent)?|(?:last|first|recent)\s+(\d+)', question_lower)
    limit_clause = ""
    if limit_match:
        limit_num = limit_match.group(1) or limit_match.group(2)
        limit_clause = f" LIMIT {limit_num}"
    
    # Check for ordering
    order_clause = ""
    if 'last' in question_lower or 'recent' in question_lower:
        order_clause = " ORDER BY id DESC"
    
    query = f"SELECT * FROM {mentioned_table}{order_clause}{limit_clause}"
    logger.info(f"Fallback query generated: {query}")
    return query


def execute_query(conn: sqlite3.Connection, query: str) -> List[Dict[str, Any]]:
    """Execute SQL query safely and return results as a list of dictionaries"""
    try:
        logger.info(f"Executing query: {query}")
        cursor = conn.execute(query)
        columns = [description[0] for description in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        logger.info(f"Query executed successfully. Returned {len(results)} rows.")
        return results
    except sqlite3.Error as e:
        logger.error(f"Error executing query: {e}")
        raise HTTPException(status_code=400, detail=f"Query execution error: {str(e)}")


# API Endpoints
@app.get("/")
async def root():
    """Root endpoint - API information"""
    logger.info("Root endpoint accessed")
    return {
        "message": "Chat with Database API",
        "version": "1.0.0",
        "endpoints": {
            "/chat": "POST - Send natural language queries",
            "/upload-csv": "POST - Upload CSV data to create temporary table",
            "/health": "GET - Health check"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    logger.info("Health check endpoint accessed")
    
    # Check database connection
    db_status = "connected"
    try:
        with get_db_connection() as conn:
            conn.execute("SELECT 1")
    except Exception as e:
        db_status = f"error: {str(e)}"
        logger.error(f"Health check failed: {e}")
    
    # Check OpenAI availability
    openai_status = "configured" if openai_client else "not configured"
    
    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "openai": openai_status
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint - accepts natural language queries and returns results.
    
    Translates natural language to SQL, executes the query, and returns structured results.
    """
    logger.info(f"Received chat request: {request.message}")
    
    try:
        with get_db_connection() as conn:
            # Get database schema
            schema = get_database_schema(conn)
            schema_str = "\n".join(
                f"Table: {table['table_name']}\nColumns: {', '.join(table['column_names'])}"
                for table in schema
            )
            
            # Generate SQL query from natural language
            sql_query = generate_sql_query(request.message, schema_str)
            
            # Execute query
            results = execute_query(conn, sql_query)
            
            # Prepare response
            row_count = len(results)
            response_message = f"Found {row_count} result(s) for your query."
            
            logger.info(f"Returning response with {row_count} rows")
            
            return ChatResponse(
                message=response_message,
                sql_query=sql_query,
                results=results,
                row_count=row_count
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...), table_name: str = "uploaded_data"):
    """
    Upload CSV file and create a temporary table in the database.
    
    This allows users to query uploaded CSV data using natural language.
    """
    logger.info(f"Received CSV upload: {file.filename}, target table: {table_name}")
    
    # Validate table name to prevent SQL injection
    if not re.match(r'^[a-zA-Z0-9_]+$', table_name):
        logger.error(f"Invalid table name: {table_name}")
        raise HTTPException(status_code=400, detail="Invalid table name. Use only letters, numbers, and underscores.")
    
    try:
        # Read CSV content
        content = await file.read()
        csv_string = content.decode('utf-8')
        
        # Parse CSV using pandas
        df = pd.read_csv(StringIO(csv_string))
        logger.info(f"CSV parsed successfully. Shape: {df.shape}")
        
        # Create table in database
        with get_db_connection() as conn:
            # pandas to_sql safely handles table creation with if_exists='replace'
            # This avoids the need for DROP TABLE which could be vulnerable
            df.to_sql(table_name, conn, index=False, if_exists='replace')
            conn.commit()
            
            logger.info(f"Table '{table_name}' created with {len(df)} rows")
            
            return {
                "message": f"CSV uploaded successfully",
                "table_name": table_name,
                "rows": len(df),
                "columns": list(df.columns)
            }
            
    except Exception as e:
        logger.error(f"Error uploading CSV: {e}")
        raise HTTPException(status_code=400, detail=f"Error processing CSV: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting FastAPI server...")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
