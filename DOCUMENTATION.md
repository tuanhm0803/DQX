# DQX Project Documentation

## Overview

DQX is a FastAPI application designed to provide a web-based interface for interacting with a PostgreSQL database using `psycopg2`. It allows users to browse tables, view table structures, query data, and manage SQL scripts. A key feature is its handling of tables within an 'STG' (staging) schema, where it enforces a specific 5-column structure for any table created in this schema.

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
    *   `get_db()`: A dependency function used by FastAPI. It creates and yields a new `psycopg2` database connection for each incoming request and ensures the connection is closed after the request is processed.

### 3. `app/models.py`

*   **Purpose**: This module previously contained SQLAlchemy ORM (Object Relational Mapper) models. After refactoring to `psycopg2`, it no longer defines ORM models. Database table definitions (like `dq.dq_sql_scripts`) are now managed directly via SQL DDL statements (e.g., executed manually or through migration scripts). Pydantic models in `app/schemas.py` are used for data validation and serialization related to API interactions.

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

*   **Purpose**: Contains the core logic for database operations (Create, Read, Update, Delete - CRUD). This module interacts directly with the database using `psycopg2`.
*   **Key Functions**:
    *   `get_table_names(db: PgConnection)`: Retrieves a list of all table names in the 'dq' schema using `psycopg2`.
    *   `get_table_structure(table_name: str, db: PgConnection)`: Fetches the column definitions (name, type, etc.) for a specified table in the 'dq' schema using `psycopg2`.
    *   `get_table_data(table_name: str, skip: int, limit: int, db: PgConnection)`: Retrieves rows from a table in the 'dq' schema with pagination support using `psycopg2`.
    *   `insert_table_data(table_name: str, data: dict, db: PgConnection)`: Inserts a new row into the specified table in the 'dq' schema using `psycopg2`.
    *   `update_table_data(table_name: str, record_id: Any, data: dict, id_column: str, db: PgConnection)`: Updates an existing row in a table in the 'dq' schema, identified by `record_id` in the specified `id_column`, using `psycopg2`.
    *   `delete_table_data(table_name: str, record_id: Any, id_column: str, db: PgConnection)`: Deletes a row from a table in the 'dq' schema by its ID using `psycopg2`.
    *   `execute_query(query_string: str, db: PgConnection)`: Executes a raw SQL `SELECT` query using `psycopg2` and returns the results.
    *   `get_sql_scripts(db: PgConnection)`: Retrieves all saved SQL scripts from the `dq.dq_sql_scripts` table using `psycopg2`.
    *   `get_sql_script(db: PgConnection, script_id: int)`: Fetches a single SQL script by its `id` from `dq.dq_sql_scripts` using `psycopg2`.
    *   `create_sql_script(db: PgConnection, script_data: SQLScriptCreate)`: Creates a new SQL script record in the `dq.dq_sql_scripts` table using `psycopg2`.
    *   `update_sql_script(db: PgConnection, script_id: int, script_data: SQLScriptCreate)`: Updates an existing SQL script in `dq.dq_sql_scripts` using `psycopg2`.
    *   `delete_sql_script(db: PgConnection, script_id: int)`: Deletes an SQL script from `dq.dq_sql_scripts` using `psycopg2`.
    *   `JSONEncoder(json.JSONEncoder)`: A custom JSON encoder to handle serialization of data types like `datetime`, `date`, `Decimal`, and `bytes` which are not natively handled by the default `json` library when processing `psycopg2` results.
    *   `_format_value_for_json(value: Any)`: Helper function to prepare individual database values for JSON serialization.
    *   `_process_result_row(row: tuple, column_names: List[str])`: Converts a database result row (tuple from `psycopg2`) into a dictionary with column names as keys and properly formatted values.
    *   `TableStructureValidationError(ValueError)`: Custom exception class raised when a table created in the `STG` schema does not meet the required column structure.
    *   The STG schema enforcement logic (previously involving `_validate_table_structure`, `_parse_create_table_statement`, etc.) is primarily encapsulated within `execute_sql_script`. This function inspects `CREATE TABLE` statements targeting the `STG` schema and may modify them or validate their structure post-execution using direct `psycopg2` operations.
    *   `execute_sql_script(db: PgConnection, script_content: str)`: The main public function in `crud.py` for executing arbitrary SQL scripts using `psycopg2`.
        *   It may parse and potentially modify `CREATE TABLE STG.*` statements to enforce column rules.
        *   It executes the script, handling DDL/DML (with commits/rollbacks) and `SELECT` queries appropriately.
        *   Catches `TableStructureValidationError` and other `psycopg2.Error` or `ValueError` exceptions, re-raising them to be handled by the API routes.

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
        *   Uses `crud.execute_sql_script`, subject to STG table column enforcement.
        *   Handles `TableStructureValidationError` and other errors.

## Frontend (`app/static/`)

*   `index.html`: The main landing page for the application.
*   `sql_editor.html`: Provides a user interface for writing and executing SQL queries, likely interacting with the `/scripts/execute` and potentially other API endpoints.

## Setup and Running

1.  **Environment Variables**: A `.env` file in the DQX root directory should define `DATABASE_URL` (e.g., `DATABASE_URL="postgresql://user:password@host:port/database"`).
2.  **Dependencies**: Install dependencies from `requirements.txt` (`pip install -r requirements.txt`).
3.  **Running**: Execute `python app/main.py` from the DQX root directory, or run using Uvicorn directly: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`.

## Key Design Considerations

*   **STG Schema Enforcement**: A primary feature is the strict column structure imposed on tables created within the `STG` schema via the SQL execution endpoint. This is handled in `crud.py` using `psycopg2`.
*   **Separation of Concerns**: The project is structured with separate modules for database logic (`database.py`), data schemas (`schemas.py`), business logic/CRUD operations (`crud.py`), and API routing (`routes/`).
*   **Dependency Injection**: FastAPI's dependency injection (`Depends(get_db)`) is used to manage `psycopg2` database connections.
*   **Error Handling**: HTTPExceptions are used in routes to return appropriate error responses. Custom exceptions like `TableStructureValidationError` are defined for specific business logic errors.
