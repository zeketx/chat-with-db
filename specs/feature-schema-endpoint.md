# Feature: GET /schema Endpoint

## Feature Description
Add a read-only `GET /schema` endpoint to `main.py` that returns the full structure of the connected SQLite database as JSON — every table with its column names and types. This gives API clients and human developers a self-service way to discover what data is queryable before sending a `/chat` request.

## User Story
As a developer or API client
I want to call `GET /schema` and receive a JSON description of all tables and their columns
So that I can compose accurate natural-language questions to `/chat` without guessing at table or column names

## Problem Statement
Users querying `/chat` frequently ask vague questions because they have no idea what tables or columns exist in the connected database. This produces poor SQL generation, confusing results, and a frustrating experience. There is no existing endpoint that exposes the database structure.

## Solution Statement
Add a `GET /schema` endpoint that connects to the database using the existing `get_db_connection()` context manager, queries `sqlite_master` for table names and `PRAGMA table_info()` for column metadata (both already used elsewhere in the codebase), and returns a typed JSON response. Errors (empty DB, unreachable file) are surfaced with clear HTTP error responses. No new DB client or dependency is needed.

## Relevant Files

- **`main.py`** — Contains all endpoint definitions, the `get_db_connection()` context manager, `get_table_names()`, `get_column_names()`, and `get_database_schema()`. The new endpoint and supporting Pydantic models live here.
- **`API_DOCUMENTATION.md`** — Must be updated to document the new endpoint with example request/response.

### New Files
_None — the feature is self-contained within existing files._

## Implementation Plan

### Phase 1: Foundation
Extend the data-access layer with a `get_column_info()` helper that returns both column name and type from `PRAGMA table_info()`. This reuses the existing pattern in `get_column_names()` (line 118–131) but captures index 2 (type) in addition to index 1 (name).

### Phase 2: Core Implementation
Add two Pydantic response models (`ColumnInfo`, `TableInfo`, `SchemaResponse`) and implement the `GET /schema` endpoint. The endpoint:
- Opens a DB connection via `get_db_connection()`
- Retrieves all tables with `get_table_names()`
- For each table fetches column info with `get_column_info()`
- Returns a `SchemaResponse` with the `tables` list
- Returns `503` if the DB is unreachable and `200` with an empty `tables: []` if the DB has no tables

### Phase 3: Integration
- Update the root `/` endpoint's `endpoints` dict to advertise `/schema`.
- Document the new endpoint in `API_DOCUMENTATION.md`.

## Step by Step Tasks

### Step 1: Add `get_column_info()` helper to `main.py`
- Below `get_column_names()` (after line 131), add a new function `get_column_info(conn, table_name) -> List[Dict[str, str]]`
- Use `PRAGMA table_info('<table_name>')` — same query already used in `get_column_names()`
- Return `[{"name": row[1], "type": row[2]} for row in cursor.fetchall()]`
- Apply the same table-name validation regex `r'^[a-zA-Z0-9_]+$'` already present in `get_column_names()`
- Log the result the same way existing helpers do

### Step 2: Add Pydantic response models for `/schema`
- After the existing `ChatResponse` model (after line 84), add:
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

### Step 3: Implement `GET /schema` endpoint in `main.py`
- Add the endpoint after the `/health` endpoint (after line 317)
- Open DB via `get_db_connection()`
- Call `get_table_names()` — if empty, return `SchemaResponse(tables=[])`
- For each table, call `get_column_info()` and build a `TableInfo`
- Return `SchemaResponse(tables=table_list)`
- Wrap in `try/except HTTPException` (re-raise) and `except Exception` → 500
- Log entry and result count

### Step 4: Update the root `/` endpoint
- In the `endpoints` dict inside `root()` (line 285–293), add:
  ```python
  "/schema": "GET - Retrieve database schema (tables and columns)"
  ```

### Step 5: Document the endpoint in `API_DOCUMENTATION.md`
- Add a new section **"5. Schema Endpoint"** after the Upload CSV section
- Include: description, HTTP method, example `curl` request, example JSON response, and error cases (empty DB, DB unreachable)

### Step 6: Run validation commands
- Execute all validation commands listed in the **Validation Commands** section and confirm zero errors

## Testing Strategy

### Unit Tests
_No test suite exists yet in this project. Validation is done via live curl commands against a running server._

### Integration Tests
- `GET /schema` against a DB with tables → returns correct tables + columns with types
- `GET /schema` against an empty DB (no tables) → returns `{"tables": []}`
- `GET /schema` with `DB_URL` pointing to a non-existent file → SQLite creates an empty file, so response is `{"tables": []}` (SQLite behavior — not an error)
- Existing endpoints (`/`, `/health`, `/chat`, `/upload-csv`) must remain unchanged

### Edge Cases
- DB has tables with no columns (degenerate schema) → `columns: []` for that table
- Table names with numbers or underscores → handled by existing validation regex
- `PRAGMA table_info()` returns empty type string (SQLite allows typeless columns) → `"type": ""` is acceptable
- Very large number of tables → response is still valid JSON, no truncation

## Acceptance Criteria
- `curl http://localhost:8000/schema` returns HTTP 200 with a JSON body matching:
  ```json
  {
    "tables": [
      {
        "name": "<table_name>",
        "columns": [
          {"name": "<col_name>", "type": "<col_type>"},
          ...
        ]
      },
      ...
    ]
  }
  ```
- An empty database returns `{"tables": []}` with HTTP 200
- No changes to the behavior or signatures of `/`, `/health`, `/chat`, or `/upload-csv`
- The endpoint is documented in `API_DOCUMENTATION.md` with a working curl example
- All log statements follow existing format (INFO level, same logger)

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

```bash
# 1. Start the server (requires DB_URL set in .env or env)
python main.py &
SERVER_PID=$!
sleep 2

# 2. Verify /schema returns valid JSON with tables
curl -s http://localhost:8000/schema | python3 -m json.tool

# 3. Verify root endpoint still lists /schema
curl -s http://localhost:8000/ | python3 -m json.tool

# 4. Verify existing endpoints are unbroken
curl -s http://localhost:8000/health | python3 -m json.tool

# 5. Smoke test /chat still works (adjust message to match your DB)
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "show me all tables"}' | python3 -m json.tool

# 6. Kill server
kill $SERVER_PID
```

## Notes
- `PRAGMA table_info()` row structure: `(cid, name, type, notnull, dflt_value, pk)` — index 1 is name, index 2 is type. This is stable across all SQLite versions.
- SQLite does not error when opening a non-existent DB file — it creates an empty one. So "unreachable DB" in practice means a permissions error or a corrupted file. The existing `get_db_connection()` already raises `HTTPException(500)` in that case, which the `/schema` endpoint inherits for free.
- No new dependencies are required. `PRAGMA table_info()` is built into SQLite's stdlib module.
- Column types in SQLite are advisory (type affinity), so the returned type strings reflect what was declared in `CREATE TABLE`, not a strict type system. This is expected and acceptable.
