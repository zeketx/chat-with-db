# Feature: Add /schema Endpoint

## Feature Description
Expose a read-only `GET /schema` endpoint that returns the full structure of the connected SQLite database — every table name along with each column's name and data type. This gives clients and humans a way to discover what is queryable before sending natural language messages to `/chat`, leading to more accurate queries and better SQL generation.

## User Story
As a developer or API client
I want to call `GET /schema` and receive the full database structure
So that I can discover available tables and columns before crafting queries for the `/chat` endpoint

## Problem Statement
Users calling `/chat` often submit vague or incorrect questions because they don't know the underlying table names or column types. There is no existing endpoint to inspect the database structure, forcing users to guess or consult out-of-band documentation.

## Solution Statement
Add a `GET /schema` endpoint to `main.py` that reuses the existing `get_db_connection()` context manager and `PRAGMA table_info()` SQLite introspection (already used by `get_column_names()`). Introduce a new `get_column_info()` helper that extends the existing pattern to return both column name and type. Return a JSON object matching the agreed-upon shape. Handle empty databases and connection errors with clear error responses. Document the endpoint in `API_DOCUMENTATION.md` and register it in the root `/` listing.

## Relevant Files

- **`main.py`** — The FastAPI server. All changes (new Pydantic models, new helper function, new endpoint, updated root listing) live here.
- **`API_DOCUMENTATION.md`** — The public API reference. The `/schema` endpoint must be documented here.

### New Files
None — the feature is self-contained within existing files.

## Implementation Plan

### Phase 1: Foundation
Add the Pydantic response models (`ColumnInfo`, `TableInfo`, `SchemaResponse`) and a `get_column_info()` helper that reads both column name and type from `PRAGMA table_info()`. The helper follows the same guard-rails already used in `get_column_names()` (table name validation, error logging, safe fallback).

### Phase 2: Core Implementation
Add the `GET /schema` endpoint. It opens a connection with `get_db_connection()`, iterates over tables via the existing `get_table_names()`, calls `get_column_info()` for each table, and returns a `SchemaResponse`. An empty database returns `{"tables": []}`. A connection error returns HTTP 500 with a clear detail message.

### Phase 3: Integration
- Update the root `/` endpoint to include `/schema` in its `endpoints` dict so the listing stays accurate.
- Document the endpoint in `API_DOCUMENTATION.md` with method, description, example request, and example response.
- Write unit and integration tests covering the happy path, empty database, and error scenarios.

## Step by Step Tasks

### Step 1: Add Pydantic response models to main.py
- After the existing `ChatResponse` model (around line 84), add three new models:
  ```python
  class ColumnInfo(BaseModel):
      name: str = Field(..., description="Column name")
      type: str = Field(..., description="Column data type")

  class TableInfo(BaseModel):
      name: str = Field(..., description="Table name")
      columns: List[ColumnInfo] = Field(..., description="List of columns")

  class SchemaResponse(BaseModel):
      tables: List[TableInfo] = Field(..., description="List of tables and their columns")
  ```

### Step 2: Add get_column_info() helper to main.py
- After `get_column_names()` (around line 131), add a new helper:
  ```python
  def get_column_info(conn: sqlite3.Connection, table_name: str) -> List[Dict[str, str]]:
      """Get column names and types for a specific table"""
      try:
          if not re.match(r'^[a-zA-Z0-9_]+$', table_name):
              logger.error(f"Invalid table name: {table_name}")
              return []
          cursor = conn.execute(f"PRAGMA table_info('{table_name}');")
          columns = [{"name": row[1], "type": row[2]} for row in cursor.fetchall()]
          logger.info(f"Table '{table_name}' column info: {columns}")
          return columns
      except sqlite3.Error as e:
          logger.error(f"Error fetching column info for table '{table_name}': {e}")
          return []
  ```
- `row[1]` is the column name and `row[2]` is the declared type — both already exposed by `PRAGMA table_info()` which is already used in `get_column_names()`.

### Step 3: Add GET /schema endpoint to main.py
- After the `/health` endpoint (around line 317), add:
  ```python
  @app.get("/schema", response_model=SchemaResponse)
  async def schema():
      """
      Schema endpoint - returns the full database structure.

      Returns every table and its columns (name + type) so clients can
      discover what is queryable before sending natural language queries.
      """
      logger.info("Schema endpoint accessed")
      try:
          with get_db_connection() as conn:
              table_names = get_table_names(conn)
              tables = [
                  TableInfo(
                      name=table_name,
                      columns=[
                          ColumnInfo(name=col["name"], type=col["type"])
                          for col in get_column_info(conn, table_name)
                      ]
                  )
                  for table_name in table_names
              ]
              return SchemaResponse(tables=tables)
      except HTTPException:
          raise
      except Exception as e:
          logger.error(f"Unexpected error in schema endpoint: {e}")
          raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
  ```

### Step 4: Update root endpoint listing in main.py
- In the `root()` function, add `"/schema"` to the `endpoints` dict:
  ```python
  "/schema": "GET - Return database schema (tables and columns)",
  ```

### Step 5: Write tests (test_schema_endpoint.py)
- Create `test_schema_endpoint.py` in the project root (alongside `main.py`).
- Use `pytest` + FastAPI `TestClient` (from `starlette.testclient`).
- Patch `DB_URL` to point to a temporary in-memory or temp-file SQLite database.
- Test cases:
  - Happy path: database with one or more tables returns correct JSON shape.
  - Empty database: returns `{"tables": []}` with HTTP 200.
  - Unreachable database: connection failure returns HTTP 500 with a `detail` field.
  - Column types: verify that declared types (TEXT, INTEGER, REAL, BLOB, NUMERIC) are returned correctly.

### Step 6: Document /schema in API_DOCUMENTATION.md
- Add a new section **"5. Schema Endpoint"** after the Upload CSV section:
  - Method, path, description.
  - Example `curl` request.
  - Example JSON response matching the agreed-upon shape.
  - Note about empty database behaviour.

### Step 7: Run validation commands
- Execute all validation commands listed in the **Validation Commands** section below to confirm zero regressions.

## Testing Strategy

### Unit Tests
- `get_column_info()` returns `[{"name": "title", "type": "TEXT"}, ...]` for a known table.
- `get_column_info()` returns `[]` for an invalid table name (SQL-injection-like string).
- `get_column_info()` returns `[]` and logs an error when `sqlite3.Error` is raised.

### Integration Tests
- `GET /schema` on a database with tables returns `200` and a valid `SchemaResponse` JSON body.
- `GET /schema` on an empty database returns `200` with `{"tables": []}`.
- `GET /schema` when the database file does not exist returns `500` with a `detail` key.
- Existing endpoints (`/`, `/health`, `/chat`) are unaffected (no regressions).

### Edge Cases
- Table with zero columns (edge case in SQLite): should return `{"name": "<table>", "columns": []}`.
- Table name containing spaces or special characters: guarded by existing regex, returns empty columns gracefully.
- Very large schema (many tables): no timeout, all tables returned.
- Column with no declared type (SQLite allows typeless columns): `type` should be `""` (empty string as returned by SQLite).

## Acceptance Criteria
- `curl http://localhost:8000/schema` returns HTTP 200 with `Content-Type: application/json`.
- Response body is a JSON object with a top-level `"tables"` array.
- Each element of `"tables"` has `"name"` (string) and `"columns"` (array of `{"name": …, "type": …}`).
- An empty database returns `{"tables": []}` — not an error.
- A missing or unreadable database file returns HTTP 500 with a `"detail"` field.
- `GET /` lists `/schema` in its `endpoints` object.
- `API_DOCUMENTATION.md` contains a dedicated `/schema` section with an example request and response.
- All existing endpoints (`/`, `/health`, `/chat`, `/upload-csv`) continue to work without change.
- All tests in `test_schema_endpoint.py` pass with `pytest`.

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

```bash
# 1. Create a throwaway test database
python -c "
import sqlite3, os
conn = sqlite3.connect('/tmp/schema_test.db')
conn.execute('CREATE TABLE films (title TEXT, director TEXT, release_year INTEGER)')
conn.execute('CREATE TABLE actors (id INTEGER PRIMARY KEY, name TEXT, age REAL)')
conn.commit()
conn.close()
print('Test database created')
"

# 2. Start the server pointing at the test database (background)
DB_URL=/tmp/schema_test.db python main.py &
SERVER_PID=$!
sleep 2

# 3. Hit /schema and pretty-print the result
curl -s http://localhost:8000/schema | python -m json.tool

# 4. Validate shape with inline Python assertion
curl -s http://localhost:8000/schema | python -c "
import sys, json
data = json.load(sys.stdin)
assert 'tables' in data, 'missing tables key'
assert len(data['tables']) == 2, f'expected 2 tables, got {len(data[\"tables\"])}'
films = next(t for t in data['tables'] if t['name'] == 'films')
col_names = [c['name'] for c in films['columns']]
assert col_names == ['title', 'director', 'release_year'], f'unexpected columns: {col_names}'
col_types = {c['name']: c['type'] for c in films['columns']}
assert col_types['release_year'] == 'INTEGER', f'wrong type: {col_types[\"release_year\"]}'
print('Schema shape assertion PASSED')
"

# 5. Verify existing endpoints are unaffected
curl -s http://localhost:8000/health | python -m json.tool
curl -s http://localhost:8000/ | python -m json.tool

# 6. Run pytest
pytest test_schema_endpoint.py -v

# 7. Stop the server
kill $SERVER_PID
```

## Notes
- `PRAGMA table_info(table_name)` returns one row per column with the layout `(cid, name, type, notnull, dflt_value, pk)`. Indexes `[1]` (name) and `[2]` (type) are used — consistent with what `get_column_names()` already does with `[1]`.
- SQLite columns can have an empty string as their declared type (affinity rules allow it). The endpoint returns whatever SQLite reports rather than normalising types.
- No new dependencies are needed — `sqlite3` is in the Python standard library and is already imported in `main.py`.
- The `get_database_schema()` helper that already exists in `main.py` returns `column_names` only (no types). Rather than changing it (which could affect `/chat`), we introduce `get_column_info()` as an additive helper — this avoids any regression in the AI query generation path.
