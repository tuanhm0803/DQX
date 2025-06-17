# DQX Project Documentation

## Overview

DQX is a FastAPI application designed to provide a web-based interface for interacting with a PostgreSQL database using `psycopg2`. It allows users to browse tables, view table structures, query data, and manage SQL scripts. The application has been refactored from an initial SQLAlchemy-based approach to use `psycopg2` for all direct database interactions, enhancing control over SQL execution and simplifying the database layer.

## Project Structure

```
DQX/
├── README.md
├── requirements.txt
├── app/
│   ├── __init__.py
│   ├── crud.py             # Core database interaction logic (Create, Read, Update, Delete) using psycopg2
│   ├── database.py         # Database connection management using psycopg2
│   ├── main.py             # FastAPI application entry point, middleware, and root routes
│   ├── models.py           # (Largely refactored, no longer contains SQLAlchemy ORM models)
│   ├── schemas.py          # Pydantic models for data validation and serialization
│   ├── routes/
│   │   ├── query.py        # API routes for executing custom SQL queries
│   │   ├── sql_scripts.py  # API routes for managing and executing saved SQL scripts
│   │   └── tables.py       # API routes for table browsing, data manipulation
│   └── static/
│       ├── index.html      # Main landing page
│       └── sql_editor.html # SQL editor interface
```

## Core Components

### 1. `app/main.py`

*   **Purpose**: Entry point for the FastAPI application.
*   **Key Functions/Features**:
    *   `app = FastAPI(...)`: Initializes the FastAPI application instance.
    *   `app.add_middleware(CORSMiddleware, ...)`: Configures Cross-Origin Resource Sharing to allow requests from any origin, which is useful for development and for UIs hosted on different domains/ports.
    *   `app.include_router(...)`: Incorporates routers from `app.routes.tables`, `app.routes.query`, and `app.routes.sql_scripts` to organize API endpoints.
    *   `app.mount("/static", ...)`: Serves static files (HTML, CSS, JS) from the `app/static` directory.
    *   `@app.get("/editor", ...)` and `@app.get("/", ...)`: Define redirect responses for specific paths to serve the `sql_editor.html` and `index.html` pages respectively.
    *   `if __name__ == "__main__": uvicorn.run(...)`: Allows the application to be run directly using Uvicorn, a fast ASGI server, for development and testing.

### 2. `app/database.py`

*   **Purpose**: Manages database connections using `psycopg2`.
*   **Key Components/Functions**:
    *   `load_dotenv()`: Loads environment variables from a `.env` file (e.g., `DATABASE_URL`).
    *   `DATABASE_URL = os.getenv(...)`: Retrieves the database connection string for `psycopg2`.
    *   `get_db()`: A dependency function used by FastAPI. It creates and yields a new `psycopg2` database connection for each incoming request and ensures the connection is closed after the request is processed. This replaces the previous SQLAlchemy session management.

### 3. `app/models.py`

*   **Purpose**: This module previously contained SQLAlchemy ORM (Object Relational Mapper) models. After refactoring to `psycopg2`, it no longer defines ORM models. Database table definitions (like `dq.dq_sql_scripts`) are now managed directly via SQL DDL statements (e.g., executed manually or through migration scripts if implemented separately). The classes remaining in `models.py` (e.g., `ExampleTable`, `SQLScript`) serve as Pydantic-like plain Python objects for internal data representation if needed, but are not tied to the database schema in an ORM fashion. Pydantic models in `app/schemas.py` are the primary source for data validation and serialization related to API interactions.

### 4. `app/schemas.py`

*   **Purpose**: Defines Pydantic models for data validation, serialization (converting data to/from JSON), and API documentation.
*   **Key Models**:
    *   `GenericModel(BaseModel)`: A flexible model that accepts a dictionary (`data: Dict[str, Any]`). Used for operations like inserting or updating table rows where the structure is not fixed beforehand.
    *   `TableData(BaseModel)`: Defines the structure for responses when fetching paginated table data. Includes `data` (list of rows), `total` (total record count), `skip` (offset), and `limit` (number of records per page).
    *   `Token(BaseModel)`: (Currently seems unused in the provided routes but is good practice for authentication) Defines a structure for JWT access tokens.
    *   `SQLScriptBase(BaseModel)`: Base schema for SQL scripts, containing `name`, `description`, and `content`.
    *   `SQLScriptCreate(SQLScriptBase)`: Schema used when creating a new SQL script. Inherits from `SQLScriptBase`.
    *   `SQLScript(SQLScriptBase)`: Schema used for representing an SQL script when returned from the API, including database-generated fields like `id`, `created_at`, and `updated_at`.
        *   `Config.orm_mode = True`: Allows Pydantic to read data directly from dictionary-like objects (which our `crud.py` functions now return after processing `psycopg2` results).

### 5. `app/crud.py`

*   **Purpose**: Contains the core logic for database operations (Create, Read, Update, Delete - CRUD). This module interacts directly with the database using `psycopg2` and its `sql` module for safe dynamic SQL query construction.
*   **Key Functions**:
    *   All CRUD functions (`get_table_names`, `get_table_structure`, `get_table_data`, `insert_table_data`, `update_table_data`, `delete_table_data`, `execute_query`, `get_sql_scripts`, `get_sql_script`, `create_sql_script`, `update_sql_script`, `delete_sql_script`, `execute_sql_script`) now accept a `psycopg2` connection object (`PgConnection`) as a parameter.
    *   SQL queries are constructed using `psycopg2.sql` objects (e.g., `sql.SQL()`, `sql.Identifier()`, `sql.Placeholder()`) to prevent SQL injection vulnerabilities.
    *   Transaction management (e.g., `db.commit()`, `db.rollback()`) is handled within each relevant CRUD function.
    *   `JSONEncoder(json.JSONEncoder)` and helper functions `_format_value_for_json`, `_process_result_row` are used to convert `psycopg2` query results (tuples) into JSON-serializable dictionaries, handling various data types like `datetime`, `Decimal`, and `bytes`.
    *   `_validate_sql_script_columns(sql_content: str)`: A private helper function that validates SQL scripts. It ensures that scripts are `SELECT` statements and contain exactly the required columns: `rule_id`, `source_id`, `source_uid`, `data_value`, and `txn_date`. This validation is case-insensitive and supports column aliases (e.g., `SELECT column_alias AS rule_id, ...`). It is used by `create_sql_script`, `update_sql_script`, and `execute_sql_script` to enforce data structure consistency.
    *   The STG schema enforcement logic (previously `_validate_table_structure`, etc.) has been removed as part of the simplification. The `execute_sql_script` function now directly executes the provided SQL content using `psycopg2`, with standard error handling for database operations. Any specific schema validation would need to be re-implemented if required.

## API Routes (`app/routes/`)

### 1. `app/routes/tables.py`

*   **Purpose**: Provides API endpoints for interacting with database tables (listing, structure, data manipulation).
*   **Key Endpoints (Functions)**:
    *   `get_tables(db: PgConnection = Depends(get_db))`: Mapped to `GET /`. Returns a list of all table names in the 'dq' schema.
    *   `get_table_structure(table_name: str, db: PgConnection = Depends(get_db))`: Mapped to `GET /{table_name}/structure`. Returns the column structure of a specific table.
    *   `get_table_data(table_name: str, skip: int = 0, limit: int = 100, db: PgConnection = Depends(get_db))`: Mapped to `GET /{table_name}/data`. Retrieves paginated data from a table.
    *   `insert_table_data(table_name: str, item: GenericModel, db: PgConnection = Depends(get_db))`: Mapped to `POST /{table_name}/data`. Inserts data into a table.
    *   `update_table_data(table_name: str, record_id: int, item: GenericModel, id_column: str = "id", db: PgConnection = Depends(get_db))`: Mapped to `PUT /{table_name}/data/{record_id}`. Updates a record in a table.
    *   `delete_table_data(table_name: str, record_id: int, id_column: str = "id", db: PgConnection = Depends(get_db))`: Mapped to `DELETE /{table_name}/data/{record_id}`. Deletes a record from a table.
*   All routes use `Depends(get_db)` for `psycopg2` connection management and include basic error handling.

### 2. `app/routes/query.py`

*   **Purpose**: Provides an API endpoint for executing custom SQL `SELECT` queries.
*   **Key Endpoints (Functions)**:
    *   `execute_query(query: str, db: PgConnection = Depends(get_db))`: Mapped to `POST /`.
        *   Accepts a SQL query string.
        *   **Restriction**: Enforces that the query must start with `SELECT` (case-insensitive).
        *   Uses `crud.execute_query` for execution.

### 3. `app/routes/sql_scripts.py`

*   **Purpose**: Provides API endpoints for managing (CRUD) and executing saved SQL scripts.
*   **Key Models**:
    *   `SQLExecuteRequest(BaseModel)`: Pydantic model for the request body of the `/execute` endpoint, expecting `script_content: str`.
*   **Key Endpoints (Functions)**:
    *   `get_scripts(db: PgConnection = Depends(get_db))`: Mapped to `GET /`. Lists all saved SQL scripts.
    *   `get_script(script_id: int, db: PgConnection = Depends(get_db))`: Mapped to `GET /{script_id}`. Retrieves a specific SQL script.
    *   `create_script(script: SQLScriptCreate, db: PgConnection = Depends(get_db))`: Mapped to `POST /`. Creates a new SQL script.
    *   `update_script(script_id: int, script: SQLScriptCreate, db: PgConnection = Depends(get_db))`: Mapped to `PUT /{script_id}`. Updates an existing SQL script.
    *   `delete_script(script_id: int, db: PgConnection = Depends(get_db))`: Mapped to `DELETE /{script_id}`. Deletes an SQL script.
    *   `execute_script(request: SQLExecuteRequest = Body(...), db: PgConnection = Depends(get_db))`: Mapped to `POST /execute`.
        *   Executes the SQL script content provided in the request body.
        *   Uses `crud.execute_sql_script`, which internally calls `_validate_sql_script_columns` to ensure the script is a `SELECT` statement with the required columns (`rule_id`, `source_id`, `source_uid`, `data_value`, `txn_date`).
        *   Handles `ValueError` (including from validation) and other database errors, returning appropriate HTTP responses.

## Frontend (`app/static/`)

*   `index.html`: The main landing page for the application.
*   `sql_editor.html`: Provides a user interface for writing and executing SQL queries, likely interacting with the `/scripts/execute` and potentially other API endpoints.

## Setup and Running

1.  **Environment Variables**: A `.env` file in the DQX root directory should define `DATABASE_URL` (e.g., `DATABASE_URL="postgresql://user:password@host:port/database"`).
2.  **Dependencies**: Install dependencies from `requirements.txt` (`pip install -r requirements.txt`).
3.  **Running**: Execute `python app/main.py` from the DQX root directory, or run using Uvicorn directly: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`.

## Key Design Considerations

*   **Database Interaction**: All database operations are now performed using `psycopg2` directly, offering fine-grained control over SQL and removing the SQLAlchemy ORM layer.
*   **SQL Safety**: `psycopg2.sql` module is used for constructing SQL queries with dynamic identifiers and placeholders, mitigating SQL injection risks.
*   **SQL Script Validation**: A strict validation (`_validate_sql_script_columns` in `crud.py`) is enforced for all saved and executed SQL scripts. They must be `SELECT` statements and output exactly five columns: `rule_id`, `source_id`, `source_uid`, `data_value`, and `txn_date`. This ensures data consistency for downstream processes.
*   **STG Schema Enforcement**: The previous complex logic for STG schema validation during `CREATE TABLE` has been removed. The `execute_sql_script` endpoint now executes scripts more directly. If specific structural enforcement for `STG` tables is needed, it would require a new implementation (e.g., parsing SQL or checking `information_schema` post-execution).
*   **Separation of Concerns**: The project maintains a structure with separate modules for database connection (`database.py`), data schemas (`schemas.py`), CRUD operations (`crud.py`), and API routing (`routes/`).
*   **Error Handling**: Global exception handling in `main.py` ensures that all unhandled backend errors return a JSON response. Frontend JavaScript in `sql_editor.html` includes robust error handling for API calls.
