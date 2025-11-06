# Chat with Database API - Documentation

## Overview

A FastAPI-based REST API that allows users to chat with a SQLite database using natural language queries. The API translates natural language to SQL, executes queries safely, and returns structured JSON responses.

## Features

- **Natural Language to SQL**: Converts plain English queries to SQL using OpenAI (with intelligent fallback when unavailable)
- **SQLite Database Support**: Works with any SQLite database
- **CSV Upload**: Upload CSV files to create temporary tables for querying
- **Safe Query Execution**: Executes SQL queries safely and returns structured JSON results
- **Comprehensive Logging**: All operations are logged to stdout
- **Health Monitoring**: Built-in health check endpoint

## Getting Started

### Prerequisites

- Python 3.7+
- SQLite database file (or the API can create one from CSV uploads)
- (Optional) OpenAI API key for advanced natural language processing

### Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables:**
   
   Create a `.env` file in the project root:
   ```
   OPENAI_API_KEY="your_openai_api_key_here"  # Optional
   DB_URL="path/to/your/database.db"
   ```

3. **Run the server:**
   ```bash
   python main.py
   ```
   
   Or using uvicorn directly:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

The API will be available at `http://localhost:8000`

## API Endpoints

### 1. Root Endpoint

**GET** `/`

Returns API information and available endpoints.

**Example Request:**
```bash
curl http://localhost:8000/
```

**Example Response:**
```json
{
  "message": "Chat with Database API",
  "version": "1.0.0",
  "endpoints": {
    "/chat": "POST - Send natural language queries",
    "/upload-csv": "POST - Upload CSV data to create temporary table",
    "/health": "GET - Health check"
  }
}
```

### 2. Health Check

**GET** `/health`

Check the health status of the API and its dependencies.

**Example Request:**
```bash
curl http://localhost:8000/health
```

**Example Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "openai": "configured"
}
```

### 3. Chat Endpoint

**POST** `/chat`

Send natural language queries to the database.

**Request Body:**
```json
{
  "message": "Show me the last 10 users"
}
```

**Example Request:**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Show me the last 10 users"}'
```

**Example Response:**
```json
{
  "message": "Found 10 result(s) for your query.",
  "sql_query": "SELECT * FROM users ORDER BY id DESC LIMIT 10",
  "results": [
    {
      "id": 12,
      "name": "Leo Martinez",
      "email": "leo@example.com",
      "age": 26,
      "created_at": "2025-11-06 18:43:53"
    }
  ],
  "row_count": 10
}
```

**Query Examples:**
- "Show me all users"
- "Get the last 5 products"
- "Show me all employees in the Engineering department"
- "List all products with price greater than 100"

### 4. Upload CSV

**POST** `/upload-csv`

Upload a CSV file to create a table in the database.

**Parameters:**
- `file`: The CSV file to upload (form-data)
- `table_name`: (Optional, query parameter) Name for the table (default: "uploaded_data")

**Example Request:**
```bash
curl -X POST "http://localhost:8000/upload-csv?table_name=employees" \
  -F "file=@employees.csv"
```

**Example Response:**
```json
{
  "message": "CSV uploaded successfully",
  "table_name": "employees",
  "rows": 5,
  "columns": ["employee_id", "name", "department", "salary"]
}
```

After uploading, you can query the data:
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Show me all employees"}'
```

## Natural Language Processing

The API supports two modes of operation:

### 1. OpenAI Mode (Recommended)
When an OpenAI API key is provided, the API uses GPT-4 to accurately translate natural language to SQL queries. This provides the most accurate and flexible query generation.

### 2. Fallback Mode
When OpenAI is not available, the API uses intelligent pattern matching to generate SQL queries:
- Detects table names mentioned in the query
- Recognizes LIMIT clauses (e.g., "last 10", "first 5")
- Handles ordering (e.g., "last" triggers DESC order)
- Falls back to listing all tables if unsure

## Architecture

The API is designed to be modular and extensible:

- **Database Layer**: Context managers for safe database connections
- **Query Generation**: Pluggable query generation (OpenAI or fallback)
- **Logging**: Comprehensive logging at all layers
- **Error Handling**: Graceful error handling with informative messages
- **Type Safety**: Pydantic models for request/response validation

## Security Considerations

- SQL queries are executed using parameterized queries where possible
- Database connections are properly managed with context managers
- Error messages are sanitized to avoid exposing sensitive information
- CSV uploads create new tables (doesn't modify existing data)

## Logging

All operations are logged to stdout with the following format:
```
2025-11-06 18:43:53,123 - main - INFO - Received chat request: Show me all users
2025-11-06 18:43:53,456 - main - INFO - Generated SQL query: SELECT * FROM users
2025-11-06 18:43:53,789 - main - INFO - Query executed successfully. Returned 12 rows.
```

## Error Handling

The API returns appropriate HTTP status codes:
- `200 OK`: Successful request
- `400 Bad Request`: Invalid query or CSV format
- `500 Internal Server Error`: Server-side errors

Error responses include a detail field:
```json
{
  "detail": "Error executing query: no such table: nonexistent_table"
}
```

## Future Enhancements

The modular architecture allows for easy integration of:
- More advanced LLM models
- Additional database backends (PostgreSQL, MySQL)
- Query result caching
- Rate limiting
- Authentication and authorization
- Query history and analytics

## Testing

You can test the API using the provided test database:

1. Create a test database:
   ```bash
   python -c "import sqlite3; conn = sqlite3.connect('test.db'); 
   conn.execute('CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)'); 
   conn.execute('INSERT INTO users VALUES (1, \"Alice\")'); 
   conn.commit()"
   ```

2. Set `DB_URL=test.db` in your `.env` file

3. Run the server and test:
   ```bash
   curl -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "Show me all users"}'
   ```

## Troubleshooting

**Issue**: "Database error: unable to open database file"
- **Solution**: Ensure the `DB_URL` in `.env` points to a valid SQLite database file or a writable location

**Issue**: "OpenAI client not available"
- **Solution**: This is expected if no API key is provided. The API will use fallback mode. Add an OpenAI API key to `.env` for better results.

**Issue**: "Error generating SQL query: Connection error"
- **Solution**: Check your OpenAI API key is valid and you have internet connectivity. The API will attempt to use fallback mode.

## Support

For issues and questions, please check the repository's issue tracker.
