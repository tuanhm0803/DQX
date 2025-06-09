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
*   **Key Features**:
    *   Initializes the FastAPI app (`app = FastAPI(title="Database Explorer API")`).
    *   Configures CORS (Cross-Origin Resource Sharing) middleware to allow requests from any origin.
    *   Includes API routers from `app.routes` for different functionalities (tables, query, SQL scripts).
    *   Mounts a `/static` directory to serve static files like HTML, CSS, and JavaScript for the frontend.
    *   Defines redirect responses for the root path (`/`) to `/static/index.html` and `/editor` to `/static/sql_editor.html`.
    *   Initializes database tables based on SQLAlchemy models (`Base.metadata.create_all(bind=engine)`).
    *   Provides a `if __name__ == "__main__":` block to run the application using Uvicorn, making it executable directly.

### 2. `app/database.py`

*   **Purpose**: Manages database connections and sessions.
*   **Key Features**:
    *   Loads database connection URL from environment variables (`.env` file) using `python-dotenv`.
    *   Creates a SQLAlchemy engine (`engine = create_engine(DATABASE_URL)`).
    *   Defines `SessionLocal` for creating database sessions (`sessionmaker`).
    *   Defines `Base` for declarative SQLAlchemy models (`declarative_base()`).
    *   Provides a dependency function `get_db()` to inject database sessions into route handlers. This ensures that a session is created for each request and closed afterward.

### 3. `app/models.py`

*   **Purpose**: Defines SQLAlchemy ORM (Object Relational Mapper) models, representing database tables as Python classes.
*   **Key Features**:
    *   `SQLScript`: Represents the `sql_scripts` table in the database. It stores saved SQL scripts with columns like `id`, `name`, `description`, `content`, `created_at`, and `updated_at`.
    *   `ExampleTable`: A sample model, likely a placeholder or for demonstration.
    *   Models inherit from `Base` (defined in `app/database.py`).

### 4. `app/schemas.py`

*   **Purpose**: Defines Pydantic models for data validation, serialization, and documentation.
*   **Key Features**:
    *   `GenericModel`: A flexible model to accept arbitrary dictionary data (`data: Dict[str, Any]`), used for inserting or updating table rows.
    *   `TableData`: Structures the response for table data requests, including the data itself, total record count, skip, and limit for pagination.
    *   `SQLScriptBase`, `SQLScriptCreate`, `SQLScript`: Define the structure for creating, reading, and returning SQL script data. `SQLScript` includes database-generated fields like `id` and timestamps. `orm_mode = True` allows these models to be created directly from SQLAlchemy model instances.

### 5. `app/crud.py`

*   **Purpose**: Contains the core logic for database operations (Create, Read, Update, Delete).
*   **Key Features**:
    *   **Table Operations**: `get_table_names`, `get_table_structure`, `get_table_data`, `insert_table_data`, `update_table_data`, `delete_table_data`.
    *   **SQL Script Management**: `get_sql_scripts`, `get_sql_script`, `create_sql_script`, `update_sql_script`, `delete_sql_script`.
    *   **Custom Query Execution**: `execute_query` (currently intended for SELECTs).
    *   **STG Schema Logic (`execute_sql_script`, `_check_and_modify_table_structure`, `_validate_table_structure`)**:
        *   The `execute_sql_script` function is the main entry point for running user-provided SQL.
        *   `_check_and_modify_table_structure`: This crucial function inspects `CREATE TABLE` statements.
            *   If a statement is `CREATE TABLE STG.table_name ...`, it's identified as an "STG candidate."
            *   It checks if the definition seems to be missing `rule_id` or `source_id`.
            *   If so, it injects the mandatory five columns: `rule_id VARCHAR(20)`, `source_id VARCHAR(20)`, `source_uid VARCHAR(500)`, `data_value VARCHAR(2000)`, `txn_date DATE` into the DDL.
            *   It does *not* apply this logic to SQL `TEMPORARY` tables or tables not explicitly in the `STG` schema.
        *   `_validate_table_structure`: After an STG candidate table is created, this function verifies that it indeed has the 5 required columns in the `STG` schema.
        *   `TableStructureValidationError`: Custom exception raised if validation fails.
    *   **Transaction Handling (`_handle_ddl_dml`, `_handle_select`)**: `execute_sql_script` delegates to these helpers. `_handle_ddl_dml` manages database transactions (begin, commit, rollback) for DDL/DML statements and incorporates the STG validation step.
    *   **JSON Serialization**: Includes a custom `JSONEncoder` and helper functions (`_format_value_for_json`, `_process_result_row`) to handle data types like `datetime`, `Decimal`, and `bytes` when returning query results.

## API Routes (`app/routes/`)

### 1. `app/routes/tables.py`

*   **Purpose**: Provides API endpoints for interacting with database tables.
*   **Endpoints**:
    *   `GET /`: Lists all table names.
    *   `GET /{table_name}/structure`: Gets the column structure of a specific table.
    *   `GET /{table_name}/data`: Retrieves data from a table with pagination (skip, limit).
    *   `POST /{table_name}/data`: Inserts new data into a table (expects data in `GenericModel` format).
    *   `PUT /{table_name}/data/{record_id}`: Updates an existing record in a table by its ID.
    *   `DELETE /{table_name}/data/{record_id}`: Deletes a record from a table by its ID.
*   All routes use the `get_db` dependency to manage database sessions and perform basic table existence checks.

### 2. `app/routes/query.py`

*   **Purpose**: Provides an API endpoint for executing custom SQL queries.
*   **Endpoints**:
    *   `POST /`: Executes a given SQL query string.
        *   **Restriction**: Currently, it only allows queries starting with `SELECT` (case-insensitive) to prevent accidental modifications via this endpoint.
*   Uses `crud.execute_query` for the actual execution.

### 3. `app/routes/sql_scripts.py`

*   **Purpose**: Provides API endpoints for managing and executing saved SQL scripts.
*   **Endpoints**:
    *   `GET /`: Lists all saved SQL scripts.
    *   `GET /{script_id}`: Retrieves a specific SQL script by its ID.
    *   `POST /`: Creates and saves a new SQL script.
    *   `PUT /{script_id}`: Updates an existing SQL script.
    *   `DELETE /{script_id}`: Deletes a SQL script.
    *   `POST /execute`: Executes the content of a provided SQL script string (passed in the request body as `script_content`).
        *   This endpoint uses `crud.execute_sql_script` and is therefore subject to the STG table column enforcement logic.
        *   Handles `TableStructureValidationError` specifically to return a detailed error message to the client.

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
