# DQX Project Documentation

## Overview

DQX is a FastAPI application designed to provide a web-based interface for interacting with a PostgreSQL database. It allows users to browse tables, view table structures, query data, and manage SQL scripts. A key feature is its handling of tables within an 'STG' (staging) schema, where it enforces a specific 5-column structure for any table created in this schema.

## Project Structure

```
DQX/
├── README.md
├── requirements.txt
├── app/
│   ├── __init__.py
│   ├── crud.py             # Core database interaction logic (Create, Read, Update, Delete)
│   ├── database.py         # Database connection and session management
│   ├── main.py             # FastAPI application entry point, middleware, and root routes
│   ├── models.py           # SQLAlchemy ORM models
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
    *   `Base.metadata.create_all(bind=engine)`: Creates database tables defined in `app/models.py` if they don't already exist, based on SQLAlchemy model definitions. This is typically run at application startup.
    *   `if __name__ == "__main__": uvicorn.run(...)`: Allows the application to be run directly using Uvicorn, a fast ASGI server, for development and testing.

### 2. `app/database.py`

*   **Purpose**: Manages database connections and sessions.
*   **Key Components/Functions**:
    *   `load_dotenv()`: Loads environment variables from a `.env` file (e.g., `DATABASE_URL`).
    *   `DATABASE_URL = os.getenv(...)`: Retrieves the database connection string.
    *   `engine = create_engine(DATABASE_URL)`: Creates a SQLAlchemy engine, which is the starting point for any SQLAlchemy application. It provides a source of database connectivity and behavior.
    *   `SessionLocal = sessionmaker(...)`: Creates a factory for producing database sessions (`Session` objects). Sessions are used to interact with the database.
    *   `Base = declarative_base()`: A factory function that returns a base class for declarative class definitions. SQLAlchemy ORM models will inherit from this base.
    *   `metadata = MetaData()`: A container object that keeps together many different features of a database (or multiple databases) being described.
    *   `get_db()`: A dependency function used by FastAPI. It creates a new database session for each incoming request and ensures the session is closed after the request is processed. This is a common pattern for managing database session lifecycles in web applications.

### 3. `app/models.py`

*   **Purpose**: Defines SQLAlchemy ORM (Object Relational Mapper) models, representing database tables as Python classes.
*   **Key Models**:
    *   `ExampleTable(Base)`: A sample SQLAlchemy model. It defines a table named `example_table` with columns `id`, `name`, and `description`. This serves as a template or placeholder.
    *   `SQLScript(Base)`: Represents the `sql_scripts` table.
        *   Columns: `id` (primary key), `name` (script name), `description` (optional details), `content` (the SQL script itself), `created_at` (timestamp of creation, defaults to current time), `updated_at` (timestamp of last update, updates automatically).
        *   This model is used to store and manage user-defined SQL scripts.

### 4. `app/schemas.py`

*   **Purpose**: Defines Pydantic models for data validation, serialization (converting data to/from JSON), and API documentation.
*   **Key Models**:
    *   `GenericModel(BaseModel)`: A flexible model that accepts a dictionary (`data: Dict[str, Any]`). Used for operations like inserting or updating table rows where the structure is not fixed beforehand.
    *   `TableData(BaseModel)`: Defines the structure for responses when fetching paginated table data. Includes `data` (list of rows), `total` (total record count), `skip` (offset), and `limit` (number of records per page).
    *   `Token(BaseModel)`: (Currently seems unused in the provided routes but is good practice for authentication) Defines a structure for JWT access tokens.
    *   `SQLScriptBase(BaseModel)`: Base schema for SQL scripts, containing `name`, `description`, and `content`.
    *   `SQLScriptCreate(SQLScriptBase)`: Schema used when creating a new SQL script. Inherits from `SQLScriptBase`.
    *   `SQLScript(SQLScriptBase)`: Schema used for representing an SQL script when returned from the API, including database-generated fields like `id`, `created_at`, and `updated_at`.
        *   `Config.orm_mode = True`: Allows Pydantic to read data directly from SQLAlchemy model instances (ORM objects).

### 5. `app/crud.py`

*   **Purpose**: Contains the core logic for database operations (Create, Read, Update, Delete - CRUD). This module interacts directly with the database using SQLAlchemy.
*   **Key Functions**:
    *   `get_table_names(db: Session)`: Retrieves a list of all table names in the connected database using SQLAlchemy's inspection capabilities.
    *   `get_table_structure(table_name: str, db: Session)`: Fetches the column definitions (name, type, etc.) for a specified table.
    *   `get_table_data(table_name: str, skip: int, limit: int, db: Session)`: Retrieves rows from a table with pagination support. It dynamically creates a SQLAlchemy `Table` object to query.
    *   `insert_table_data(table_name: str, data: dict, db: Session)`: Inserts a new row into the specified table.
    *   `update_table_data(table_name: str, record_id: int, data: dict, id_column: str, db: Session)`: Updates an existing row in a table, identified by `record_id` in the specified `id_column`.
    *   `delete_table_data(table_name: str, record_id: int, id_column: str, db: Session)`: Deletes a row from a table by its ID.
    *   `execute_query(query: str, db: Session)`: Executes a raw SQL query (intended primarily for `SELECT` statements as per `app/routes/query.py`) and returns the results.
    *   `get_sql_scripts(db: Session)`: Retrieves all saved SQL scripts from the `sql_scripts` table.
    *   `get_sql_script(db: Session, script_id: int)`: Fetches a single SQL script by its `id`.
    *   `create_sql_script(db: Session, script: SQLScriptCreate)`: Creates a new SQL script record in the database.
    *   `update_sql_script(db: Session, script_id: int, script: SQLScriptCreate)`: Updates an existing SQL script.
    *   `delete_sql_script(db: Session, script_id: int)`: Deletes an SQL script from the database.
    *   `JSONEncoder(json.JSONEncoder)`: A custom JSON encoder to handle serialization of data types like `datetime`, `date`, `Decimal`, and `bytes` which are not natively handled by the default `json` library.
    *   `_format_value_for_json(value: Any)`: Helper function to prepare individual database values for JSON serialization using the custom logic.
    *   `_process_result_row(row: tuple, column_names: List[str])`: Converts a database result row (tuple) into a dictionary with column names as keys and properly formatted values.
    *   `TableStructureValidationError(ValueError)`: Custom exception class raised when a table created in the `STG` schema does not meet the required column structure.
    *   `_validate_table_structure(db: Session, table_name: str, is_temporary: bool)`: Checks if a table (specified by `table_name` and whether it's a SQL `TEMPORARY` table) in the `STG` schema (or a temporary schema for `TEMPORARY` tables) has the five mandatory columns (`rule_id`, `source_id`, `source_uid`, `data_value`, `txn_date`). Raises `TableStructureValidationError` if not.
    *   `_parse_create_table_statement(script_content: str)`: Uses regex to parse a `CREATE TABLE` SQL statement, extracting components like whether it's `TEMPORARY`, if `IF NOT EXISTS` is used, the schema prefix (e.g., `STG.`), the base table name, and the rest of the DDL.
    *   `_determine_column_injection_necessity(parsed_info: Dict[str, Any])`: Based on the parsed `CREATE TABLE` statement (specifically the column definition part or if it's a `CREATE TABLE AS SELECT`), this function determines if the mandatory STG columns (`rule_id`, `source_id`) appear to be missing from the explicit column definitions.
    *   `_inject_stg_columns(parsed_info: Dict[str, Any], ddl_table_name_part: str)`: Modifies the parsed `CREATE TABLE` DDL string to include the five mandatory STG columns. It handles cases where columns are defined explicitly (e.g., `CREATE TABLE STG.foo (col1 INT, ...)`) and `CREATE TABLE AS SELECT` statements.
    *   `_check_and_modify_table_structure(script_content: str)`: This is a key function for STG schema enforcement.
        *   It first parses the SQL script using `_parse_create_table_statement`.
        *   If the statement is `CREATE TABLE STG.table_name ...` (i.e., explicitly targets the `STG` schema), it's considered an "STG candidate."
        *   For STG candidates, it uses `_determine_column_injection_necessity` to see if the standard columns are missing.
        *   If they are missing, it calls `_inject_stg_columns` to add them to the DDL.
        *   It returns the (potentially modified) script, the base table name if it was an STG candidate (for later validation), and a boolean indicating if the SQL `TEMPORARY` keyword was used.
        *   It does *not* modify tables unless they are explicitly created with the `STG.` prefix. SQL `TEMPORARY` tables are not modified for STG compliance unless they also have the `STG.` prefix (e.g. `CREATE TEMPORARY TABLE STG.my_temp_table ...`).
    *   `_handle_ddl_dml(db: Session, sql: Any, table_name_to_validate: Optional[str], is_sql_temporary_table: bool)`: Manages the execution of DDL (Data Definition Language, e.g., `CREATE`, `ALTER`) and DML (Data Manipulation Language, e.g., `INSERT`, `UPDATE`, `DELETE`) statements.
        *   It ensures operations are wrapped in a database transaction (begin, commit, rollback).
        *   If `table_name_to_validate` is provided (meaning an explicit `STG.` table was created/altered), it calls `_validate_table_structure` *after* the DDL execution but *before* committing the transaction.
        *   Returns a message and affected row count.
    *   `_handle_select(db: Session, sql: Any)`: Manages the execution of `SELECT` queries. It fetches results, processes rows for JSON compatibility, and returns the data.
    *   `execute_sql_script(db: Session, script_content: str)`: The main public function in `crud.py` for executing arbitrary SQL scripts.
        *   It first checks if the script contains a `CREATE TABLE` statement. If so, it calls `_check_and_modify_table_structure` to enforce STG column rules if applicable.
        *   It then determines if the script is DDL/DML or a `SELECT` query based on keywords.
        *   Delegates execution to `_handle_ddl_dml` or `_handle_select` accordingly.
        *   Catches `TableStructureValidationError` and other exceptions, re-raising them to be handled by the API routes.

## API Routes (`app/routes/`)

### 1. `app/routes/tables.py`

*   **Purpose**: Provides API endpoints for interacting with database tables (listing, structure, data manipulation).
*   **Key Endpoints (Functions)**:
    *   `get_tables(db: Session = Depends(get_db))`: Mapped to `GET /`. Returns a list of all table names using `crud.get_table_names`.
    *   `get_table_structure(table_name: str, db: Session = Depends(get_db))`: Mapped to `GET /{table_name}/structure`. Returns the column structure of a specific table using `crud.get_table_structure`. Includes a check if the table exists.
    *   `get_table_data(table_name: str, skip: int = 0, limit: int = 100, db: Session = Depends(get_db))`: Mapped to `GET /{table_name}/data`. Retrieves paginated data from a table using `crud.get_table_data`.
    *   `insert_table_data(table_name: str, item: GenericModel, db: Session = Depends(get_db))`: Mapped to `POST /{table_name}/data`. Inserts data (provided in `item.data`) into a table using `crud.insert_table_data`.
    *   `update_table_data(table_name: str, record_id: int, item: GenericModel, id_column: str = "id", db: Session = Depends(get_db))`: Mapped to `PUT /{table_name}/data/{record_id}`. Updates a record in a table using `crud.update_table_data`.
    *   `delete_table_data(table_name: str, record_id: int, id_column: str = "id", db: Session = Depends(get_db))`: Mapped to `DELETE /{table_name}/data/{record_id}`. Deletes a record from a table using `crud.delete_table_data`.
*   All routes use `Depends(get_db)` for session management and include basic error handling (e.g., table not found, operation failed).

### 2. `app/routes/query.py`

*   **Purpose**: Provides an API endpoint for executing custom SQL `SELECT` queries.
*   **Key Endpoints (Functions)**:
    *   `execute_query(query: str, db: Session = Depends(get_db))`: Mapped to `POST /`.
        *   Accepts a SQL query string.
        *   **Restriction**: Enforces that the query must start with `SELECT` (case-insensitive) to prevent modifications through this specific endpoint.
        *   Uses `crud.execute_query` for execution and returns the results.
        *   Includes basic error handling.

### 3. `app/routes/sql_scripts.py`

*   **Purpose**: Provides API endpoints for managing (CRUD) and executing saved SQL scripts.
*   **Key Models**:
    *   `SQLExecuteRequest(BaseModel)`: Pydantic model for the request body of the `/execute` endpoint, expecting `script_content: str`.
*   **Key Endpoints (Functions)**:
    *   `get_scripts(db: Session = Depends(get_db))`: Mapped to `GET /`. Lists all saved SQL scripts using `crud.get_sql_scripts`.
    *   `get_script(script_id: int, db: Session = Depends(get_db))`: Mapped to `GET /{script_id}`. Retrieves a specific SQL script by ID using `crud.get_sql_script`.
    *   `create_script(script: SQLScriptCreate, db: Session = Depends(get_db))`: Mapped to `POST /`. Creates a new SQL script using `crud.create_sql_script`.
    *   `update_script(script_id: int, script: SQLScriptCreate, db: Session = Depends(get_db))`: Mapped to `PUT /{script_id}`. Updates an existing SQL script using `crud.update_sql_script`.
    *   `delete_script(script_id: int, db: Session = Depends(get_db))`: Mapped to `DELETE /{script_id}`. Deletes an SQL script using `crud.delete_sql_script`.
    *   `execute_script(request: SQLExecuteRequest = Body(...), db: Session = Depends(get_db))`: Mapped to `POST /execute`.
        *   Executes the SQL script content provided in the request body (`request.script_content`).
        *   Uses `crud.execute_sql_script`, which means it is subject to the STG table column enforcement and validation logic defined in `crud.py`.
        *   Specifically handles `TableStructureValidationError` from `crud.py` to return a detailed 400 error to the client if STG table rules are violated.
        *   Includes general error handling for other execution issues.

## Frontend (`app/static/`)

*   `index.html`: The main landing page for the application.
*   `sql_editor.html`: Provides a user interface for writing and executing SQL queries, likely interacting with the `/scripts/execute` and potentially other API endpoints.

## Setup and Running

1.  **Environment Variables**: A `.env` file in the DQX root directory should define `DATABASE_URL` (e.g., `DATABASE_URL="postgresql://user:password@host:port/database"`).
2.  **Dependencies**: Install dependencies from `requirements.txt` (`pip install -r requirements.txt`).
3.  **Running**: Execute `python app/main.py` from the DQX root directory, or run using Uvicorn directly: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`.

## Key Design Considerations

*   **STG Schema Enforcement**: A primary feature is the strict column structure imposed on tables created within the `STG` schema via the SQL execution endpoint. This is handled in `crud.py`.
*   **Separation of Concerns**: The project is structured with separate modules for database logic (`database.py`), ORM models (`models.py`), data schemas (`schemas.py`), business logic/CRUD operations (`crud.py`), and API routing (`routes/`).
*   **Dependency Injection**: FastAPI's dependency injection (`Depends(get_db)`) is used to manage database sessions.
*   **Error Handling**: HTTPExceptions are used in routes to return appropriate error responses. Custom exceptions like `TableStructureValidationError` are defined for specific business logic errors.
