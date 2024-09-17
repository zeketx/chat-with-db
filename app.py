# These lines are typically run in the terminal to set up a virtual environment
# python3 -m venv venv
# source venv/bin/activate

# Import necessary libraries
import sqlite3  # For interacting with SQLite database
from openai import OpenAI  # For using OpenAI's API
import os  # For interacting with the operating system
from dotenv import load_dotenv  # For loading environment variables
import json
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt


load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
db_url = os.getenv("DB_URL")

# Connect to db
connect = sqlite3.connect(db_url)

def get_table_names():
    """Get all table names from the database"""
    table_names = []
    tables = connect.execute("SELECT name FROM sqlite_master WHERE type='table';")
    for tables in tables.fetchall():
        table_names.append(tables[0])
    return table_names

def get_column_names(table_name):
    """Get all column names for a specific table"""
    column_names = []
    columns = connect.execute(f"PRAGMA table_info('{table_name}');").fetchall()
    for col in columns:
        column_names.append(col[1])  
    return column_names

def get_database_info():
    """Get information about all tables and their columns in the database"""
    table_dicts = []
    for table_name in get_table_names():
        column_names = get_column_names(table_name)
        table_dicts.append({"table_name": table_name, "column_names": column_names})
    return table_dicts

# Get the database schema information
databaseSchema = get_database_info()

# Convert the database schema to a string format
databaseSchema_toString = "\n".join(
    f"Table: {table['table_name']}\nColumns: {', '.join(table['column_names'])}" for table in databaseSchema
)


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
                            {databaseSchema_toString}
                            Ensure that the SQL query is written in plain text and accurately reflects the schema provided.
                        """,
                    },
                },
                "required": ["query"],
            },
        }
    }
]
@st.cache_data
def ask_database(query):
    """Execute SQL query and return a DataFrame."""
    with sqlite3.connect(db_url) as conn:
        df = pd.read_sql_query(query, conn)
    return df

# Initialize the OpenAI client
client = OpenAI(
    api_key=api_key
)
def get_sql_query(question):
    chat_completion = client.chat.completions.create(
        messages = [
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
    query = eval(message.tool_calls[0].function.arguments)['query']
    return query

st.title("Database Query App")

question = st.text_input("Ask a question about the database:")
        
def is_data_visualizable(df):
    """Check if data can produce at least one plot type."""
    numeric_columns = df.select_dtypes(include=['int64', 'float64']).columns
    return len(numeric_columns) > 0, len(numeric_columns) > 1


def generate_visualization(df, plot_type, placeholder):
    """Generate visualization based on the plot type."""
    numeric_columns = df.select_dtypes(include=['int64', 'float64']).columns
    
    if plot_type == "Bar Chart" and len(numeric_columns) > 0:
        plt.figure(figsize=(10, 6))
        df.plot(kind='bar', y=numeric_columns[0], ax=plt.gca())
        plt.title(f'{numeric_columns[0]} by Index')
        plt.tight_layout()
        placeholder.pyplot(plt)
    elif plot_type == "Scatter Plot" and len(numeric_columns) > 1:
        plt.figure(figsize=(10, 6))
        df.plot(kind='scatter', x=numeric_columns[0], y=numeric_columns[1], ax=plt.gca())
        plt.title(f'{numeric_columns[1]} vs {numeric_columns[0]}')
        plt.tight_layout()
        placeholder.pyplot(plt)



if question:
    try:
        sql_query = get_sql_query(question)  # Assume get_sql_query is defined elsewhere
        results = ask_database(sql_query)
        st.subheader("SQL Query:")
        st.code(sql_query, language="sql")
        st.subheader("Query Results:")
        st.dataframe(results)
        
        can_plot_bar, can_plot_scatter = is_data_visualizable(results)
        
        if can_plot_bar or can_plot_scatter:
            # Setup layout: columns for control and visualization
            col1, col2 = st.columns([1, 3])  # Adjust column width ratio as needed
            with col1:
                plot_types = []
                if can_plot_bar:
                    plot_types.append("Bar Chart")
                if can_plot_scatter:
                    plot_types.append("Scatter Plot")
                plot_type = st.radio("Select Plot Type:", plot_types)

            with col2:
                generate_visualization(results, plot_type, col2)
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")

# Close the database connection when the app is done
connect.close()