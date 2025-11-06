# chat-with-db
This app connects to an SQLite database and allows users to ask questions about the data by generating SQL queries via OpenAI's API. It executes these queries, displays the results, and provides visualizations for data that can be graphed.

## Available Interfaces

### 1. FastAPI REST API (main.py) - NEW!
A production-ready REST API for programmatic access to chat with database functionality.

### 2. Streamlit Web UI (app.py)
An interactive web-based interface with data visualization capabilities.

## Features

-   **Natural Language to SQL:** Ask questions in plain English, and the application will convert them into the appropriate SQL query.
-   **SQLite Database Support:** Designed to work with SQLite databases.
-   **CSV Upload Support (API):** Upload CSV files to query custom data.
-   **Data Visualization (Streamlit):** Optionally display query results as a bar chart or a scatter plot.
-   **RESTful API (FastAPI):** Programmatic access for integrations.
-   **Comprehensive Logging:** All operations logged to stdout.

## Getting Started

### Prerequisites

-   Python 3.7+
-   An OpenAI API key (get one from [https://platform.openai.com/](https://platform.openai.com/))
-   A SQLite database file
-  (Optional) `.env` file for secrets

### Installation

1.  **Clone the repository:**
    ```bash
    git clone [YOUR_REPOSITORY_URL]
    cd [YOUR_REPOSITORY_NAME]
    ```
2.  **Create a virtual environment (optional but recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Linux/macOS
    # venv\Scripts\activate  # On Windows
    ```
3.  **Install the required packages:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Set up environment variables:**
    - Create a `.env` file in the project root directory.
    - Add the following lines to the `.env` file, replacing the placeholders with your actual values:
      ```
      OPENAI_API_KEY="YOUR_OPENAI_API_KEY"
      DB_URL="path/to/your/database.db"
      ```

      If you don't want to use a `.env` file, you can set the environment variables directly in your terminal.
5.  **Run the application:**

    **Option A: FastAPI REST API (recommended for integrations)**
    ```bash
    python main.py
    ```
    The API will be available at `http://localhost:8000`
    See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for full API documentation.

    **Option B: Streamlit Web UI**
    ```bash
    streamlit run app.py
    ```
    This will open the application in your browser.

## Example

Let's assume you have a SQLite database named `movies.db` with a table called `films` that contains data about movies, including columns like `title`, `director`, and `release_year`.

1.  **Launch the application** as described in the "Getting Started" steps.
2.  **Enter a question** in the text input box, such as:

    ```
   "What are the titles and release years of all the movies?"
    ```

3.  **The application will:**
    - Generate a SQL query equivalent to `SELECT title, release_year FROM films;`
    - Execute the query against your `movies.db` database.
    - Display the results in a table.
    - If the results have numerical data (like `release_year` in this case), it will give you the option to generate a bar chart (y-axis being release_year, and x-axis being the index).
    - If the results had at least 2 columns with numerical values, you will also have the option to create a scatter plot.

## Code Overview

-   **`main.py`:** FastAPI REST API server with `/chat` endpoint for natural language database queries and `/upload-csv` for CSV data upload.
-   **`app.py`:** Streamlit web UI with database interaction, SQL query generation with OpenAI, and data visualization.
-   **`requirements.txt`:** Lists all the required Python packages for both interfaces.
-   **`.env`:** Stores the configuration variables like the API key and database URL.
-   **`API_DOCUMENTATION.md`:** Complete documentation for the FastAPI REST API.

## Quick API Examples

```bash
# Health check
curl http://localhost:8000/health

# Query the database
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Show me the last 10 users"}'

# Upload CSV data
curl -X POST "http://localhost:8000/upload-csv?table_name=employees" \
  -F "file=@employees.csv"
```

For complete API documentation, see [API_DOCUMENTATION.md](API_DOCUMENTATION.md).

## Project Structure
