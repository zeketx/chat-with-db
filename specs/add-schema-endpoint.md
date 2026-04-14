# Feature: GET /schema Endpoint

## Feature Description
Add a read-only `GET /schema` endpoint to the FastAPI server (`main.py`) that introspects the connected SQLite database and returns a structured JSON object listing every table along with its columns (name and type). This gives API clients and humans a discovery mechanism to understand what data is queryable before sending natural language questions to `/chat`.

## User Story
As an API client or developer
I want to call `GET /schema` and receive the full list of tables and their columns
So that I can write better natural language queries to `/chat` by knowing exactly what data is available in the database

## Problem Statement
Users querying `/chat` often don't know what tables or columns exist in the connected SQLite database. This leads to vague questions, poor SQL generation, and failed queries. There is no discovery endpoint today — clients must either guess or inspect the database file manually.

## Solution Statement
Expose a new `GET /schema` endpoint that uses the existing `get_db_connection()` context manager and `PRAGMA table_info()` introspection (already used internally by `get_column_names()`) to return a typed JSON response of the form:

```json
{
  "tables": [
    {
      "name": "films",
      "columns": [
        {"name": "title", "type": "TEXT"},
        {"name": "director", "type": "TEXT"},
        {"name": "release_year", "type": "INTEGER"}
      ]
    }
  ]
}
```

Handle empty databases (zero tables) by returning `{"tables": []}`. Handle unreachable databases by returning a `500` HTTP error with a clear message — consistent with how `/health` and `/chat` handle DB failures.

## Relevant Files

- **`main.py`** — The FastAPI server. This is the only file that changes: add Pydantic response models (`ColumnInfo`, `TableInfo`, `SchemaResponse`) and the `GET /schema` route handler. Reuse `get_db_connection()`, `get_table_names()`, and a new `get_column_info()` helper built on the existing `PRAGMA table_info` pattern in `get_column_names()`.
- **`API_DOCUMENTATION.md`** — Add a new "Schema Endpoint" section documenting the request, response shape, and a `curl` example.
- **`test_main.py`** — New test file using FastAPI's `TestClient` and an in-memory SQLite fixture to cover the happy path, empty DB, and error cases.

### New Files
- **`test_main.py`** — Pytest test suite for `main.py`. Uses `fastapi.testclient.TestClient` and monkeypatching to test the `/schema` endpoint in isolation without a real database on disk.

## Implementation Plan

### Phase 1: Foundation
Introduce the Pydantic response models (`ColumnInfo`, `TableInfo`, `SchemaResponse`) into `main.py` and a `get_column_info()` helper that wraps the existing `PRAGMA table_info` logic to return both column name and type.

### Phase 2: Core Implementation
Add the `GET /schema` route handler that:
1. Opens a DB connection via the existing `get_db_connection()` context manager.
2. Calls `get_table_names()` to list tables.
3. Calls `get_column_info()` per table.
4. Returns a `SchemaResponse` with the assembled structure.
5. Catches `HTTPException` and DB errors, returning `500` with a clear message when the DB is unreachable.

### Phase 3: Integration
- Update `API_DOCUMENTATION.md` with the new endpoint section.
- Update the root `/` endpoint's `endpoints` dict to include `/schema`.
- Write and run `test_main.py` to validate all cases pass.

## Step by Step Tasks

### Step 1: Add `get_column_info()` helper to `main.py`
- After the existing `get_column_names()` function (line 118), add a new function `get_column_info(conn, table_name) -> List[Dict[str, str]]`.
- Use the same `PRAGMA table_info('{table_name}')` query already in `get_column_names()`.
- Return `[{"name": row[1], "type": row[2]} for row in cursor.fetchall()]`.
- Validate `table_name` with the same `re.match(r'^[a-zA-Z0-9_]+$', table_name)` guard already present in `get_column_names()`.
- Log the result at `INFO` level, consistent with `get_column_names()`.

### Step 2: Add Pydantic response models to `main.py`
- After the existing `ChatResponse` model, add three new models:
  ```python
  class ColumnInfo(BaseModel):
      name: str
      type: str

  class TableInfo(BaseModel):
      name: str
      columns: List[ColumnInfo]

  class SchemaResponse(BaseModel):
      tables: List[TableInfo]
  ```

### Step 3: Add the `GET /schema` route handler to `main.py`
- Add after the `/health` endpoint.
- Signature: `@app.get("/schema", response_model=SchemaResponse)`
- Open connection with `get_db_connection()`.
- Call `get_table_names(conn)` to get all table names.
- For each table, call `get_column_info(conn, table_name)` and build a `TableInfo`.
- Return `SchemaResponse(tables=[...])`.
- Wrap in `try/except HTTPException` + bare `except Exception` → raise `HTTPException(status_code=500, detail=...)`, consistent with the `/chat` handler.
- Log endpoint access and result count at `INFO`.

### Step 4: Update root endpoint to list `/schema`
- In the `root()` handler, add `"/schema": "GET - Retrieve database schema"` to the `endpoints` dict.

### Step 5: Write tests in `test_main.py`
- Use `fastapi.testclient.TestClient(app)` and `monkeypatch` (or override `get_db_connection`) to avoid needing a real DB file.
- Use an in-memory SQLite DB fixture:
  ```python
  import sqlite3
  from contextlib import contextmanager

  @pytest.fixture
  def db_with_tables(monkeypatch):
      conn = sqlite3.connect(":memory:")
      conn.row_factory = sqlite3.Row
      conn.execute("CREATE TABLE films (title TEXT, director TEXT, release_year INTEGER)")
      conn.commit()
      @contextmanager
      def mock_get_db():
          yield conn
      monkeypatch.setattr("main.get_db_connection", mock_get_db)
      yield conn
      conn.close()
  ```
- **Test cases:**
  1. `test_schema_returns_tables_and_columns` — happy path, checks response structure matches the example.
  2. `test_schema_empty_database` — DB with no tables returns `{"tables": []}` with status 200.
  3. `test_schema_db_error` — monkeypatch `get_db_connection` to raise `sqlite3.Error`; expect 500 response.
  4. `test_schema_column_types` — verify that column types (`TEXT`, `INTEGER`, etc.) are correctly returned.

### Step 6: Update `API_DOCUMENTATION.md`
- Add a new "5. Schema Endpoint" section after the "Upload CSV" section.
- Include: description, `GET /schema` heading, example `curl` command, example response JSON, and a note about the empty-database case.

### Step 7: Run validation commands
- See `Validation Commands` section below.

## Testing Strategy

### Unit Tests
- `get_column_info()` returns correct `[{"name": ..., "type": ...}]` from `PRAGMA table_info`.
- Invalid table name (SQL injection attempt) returns empty list without raising.

### Integration Tests
- `GET /schema` with a DB containing multiple tables returns the full schema.
- `GET /schema` with an empty DB returns `{"tables": []}` and status 200.
- `GET /schema` when DB is unreachable returns status 500 with a `detail` field.

### Edge Cases
- Database file path is valid but the file contains no tables (`{"tables": []}` — not an error).
- Table exists but has no columns — returns `{"name": "...", "columns": []}`.
- Column `type` is an empty string (SQLite allows this) — return it as-is.
- Table name contains only underscores / numbers — passes validation.
- Concurrent requests to `/schema` — each opens its own short-lived connection via `get_db_connection()` context manager; no state is shared.

## Acceptance Criteria
- `curl http://localhost:8000/schema` returns HTTP 200 with valid JSON matching `{"tables": [...]}`.
- Each table entry contains `"name"` (string) and `"columns"` (array of `{"name": string, "type": string}`).
- An empty database returns `{"tables": []}` with HTTP 200.
- An unreachable database returns HTTP 500 with a `"detail"` field.
- No changes to the behavior of `/`, `/health`, `/chat`, or `/upload-csv`.
- `/schema` is documented in `API_DOCUMENTATION.md` with a `curl` example and example response.
- All tests in `test_main.py` pass.

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

```bash
# 1. Create a test database and run the server (in one terminal)
python -c "
import sqlite3
conn = sqlite3.connect('/tmp/schema_test.db')
conn.execute('CREATE TABLE films (title TEXT, director TEXT, release_year INTEGER)')
conn.execute(\"INSERT INTO films VALUES ('Inception', 'Nolan', 2010)\")
conn.commit()
conn.close()
print('Test DB created at /tmp/schema_test.db')
"

# 2. Run server with the test DB
DB_URL=/tmp/schema_test.db python main.py &
sleep 2

# 3. Validate /schema response shape
curl -s http://localhost:8000/schema | python -m json.tool

# 4. Validate /schema returns the films table with correct columns/types
curl -s http://localhost:8000/schema | python -c "
import sys, json
data = json.load(sys.stdin)
assert 'tables' in data, 'Missing tables key'
assert len(data['tables']) == 1, f\"Expected 1 table, got {len(data['tables'])}\"
t = data['tables'][0]
assert t['name'] == 'films', f\"Expected films, got {t['name']}\"
cols = {c['name']: c['type'] for c in t['columns']}
assert cols['title'] == 'TEXT', cols
assert cols['director'] == 'TEXT', cols
assert cols['release_year'] == 'INTEGER', cols
print('Schema shape validation PASSED')
"

# 5. Validate existing endpoints still work
curl -s http://localhost:8000/health | python -m json.tool
curl -s http://localhost:8000/ | python -m json.tool

# 6. Run pytest suite
python -m pytest test_main.py -v

# 7. Kill the test server
pkill -f "python main.py"
```

- `python -m pytest test_main.py -v` — Run all tests with verbose output; all must pass.

## Notes
- The existing `get_column_names()` function is kept unchanged — it is still used by `get_database_schema()` which is used by `/chat` for schema context passed to OpenAI. The new `get_column_info()` is additive.
- `PRAGMA table_info` returns `type` as declared in the `CREATE TABLE` statement. SQLite's type affinity rules mean the value may be empty string or any freeform text. The endpoint returns it verbatim — no normalization needed.
- No new dependencies are required. `fastapi`, `sqlite3`, and `pydantic` are already in use.
- `pytest` and `httpx` (required by `TestClient`) should be added as dev dependencies if not present: `pip install pytest httpx`. This does not change `requirements.txt` for production.
- The `/schema` endpoint is intentionally read-only and does not accept any query parameters or body.
