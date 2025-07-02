# DQX Project Documentation

## Overview

DQX is a FastAPI application designed to provide a web-based interface for interacting with a PostgreSQL database using `psycopg2`. It allows users to browse tables, view table structures, query data, and manage SQL scripts. The application has been refactored from an initial SQLAlchemy-based approach to use `psycopg2` for all direct database interactions, enhancing control over SQL execution and simplifying the database layer.

## Project Structure

```
DQX/
├── README.md
├── DOCUMENTATION.md
├── requirements.txt
├── app/
│   ├── __init__.py
│   ├── crud.py             # Core database interaction logic (Create, Read, Update, Delete) using psycopg2
│   ├── database.py         # Database connection management using psycopg2
│   ├── main.py             # FastAPI application entry point, middleware, and root routes
│   ├── models.py           # Data models for the application
│   ├── schemas.py          # Pydantic models for data validation and serialization
│   ├── auth.py             # Authentication and authorization logic
│   ├── dependencies.py     # Shared dependencies for routes
│   ├── dependencies_auth.py # Authentication-related dependencies
│   ├── routes/
│   │   ├── auth.py         # Authentication routes (login, registration)
│   │   ├── bad_detail.py   # Routes for bad detail query functionality
│   │   ├── query.py        # API routes for executing custom SQL queries
│   │   ├── reference_tables.py # Routes for managing rule and source references
│   │   ├── scheduler.py    # Routes for job scheduling
│   │   ├── sql_scripts.py  # API routes for managing and executing saved SQL scripts
│   │   ├── stats.py        # Routes for statistics and visualization
│   │   └── tables.py       # API routes for table browsing, data manipulation
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css   # Shared CSS styles for consistent UI
│   │   └── js/             # JavaScript files
│   └── templates/
│       ├── index.html      # Main landing page
│       ├── bad_detail_query.html # Bad detail query interface
│       ├── visualization.html    # Data visualization interface
│       ├── scheduler.html  # Job scheduler interface
│       ├── reference_tables.html # Reference tables management
│       ├── partials/       # Reusable template components
│       └── sql_editor.html # SQL editor interface
└── utils/
    ├── __init__.py
    ├── create_tables.py    # Utility to create database tables
    └── create_users_table.py # Utility to create user authentication tables
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
    *   **Staging Table Management**: The `crud` module now manages dedicated staging tables for each saved SQL script.
        *   `create_sql_script`: When a script is created, a corresponding table named `stg.dq_script_{id}` is automatically created. Its structure is defined by the `SELECT` statement of the script (`CREATE TABLE ... AS ... WITH NO DATA`).
        *   `delete_sql_script`: When a script is deleted, its corresponding staging table (`stg.dq_script_{id}`) is automatically dropped.
        *   `populate_script_result_table`: This new function populates the dedicated staging table. It first ensures the table exists (creating it if necessary, for older scripts), then truncates it, and finally inserts the results of the script's execution into it (`INSERT INTO ... SELECT ...`).
    *   `publish_script_results(db: PgConnection, script_id: int)`: This new function merges the data from a script's staging table (`stg.dq_script_{id}`) into the central `dq.bad_detail` table. For each unique `(rule_id, source_id)` pair found in the staging table, it first deletes any existing records in `dq.bad_detail` that match the pair, and then inserts the new records from the staging table. This ensures the publishing operation is idempotent for each composite key.

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

*   **Purpose**: Provides API endpoints for managing (CRUD) and executing saved SQL scripts, including populating their dedicated staging tables.
*   **Key Models**:
    *   `SQLExecuteRequest(BaseModel)`: Pydantic model for the request body of the `/execute` endpoint, expecting `script_content: str`.
*   **Key Endpoints (Functions)**:
    *   `get_scripts(db: PgConnection = Depends(get_db))`: Mapped to `GET /`. Lists all saved SQL scripts.
    *   `get_script(script_id: int, db: PgConnection = Depends(get_db))`: Mapped to `GET /{script_id}`. Retrieves a specific SQL script.
    *   `create_script(script: SQLScriptCreate, db: PgConnection = Depends(get_db))`: Mapped to `POST /`. Creates a new SQL script.
    *   `update_script(script_id: int, script: SQLScriptCreate, db: PgConnection = Depends(get_db))`: Mapped to `PUT /{script_id}`. Updates an existing SQL script.
    *   `delete_script(script_id: int, db: PgConnection = Depends(get_db))`: Mapped to `DELETE /{script_id}`. Deletes an SQL script.
    *   `execute_script(...)`: Mapped to `POST /execute`. Executes a script's content directly.
    *   `populate_table(script_id: int, ...)`: Mapped to `POST /{script_id}/populate_table`. This new endpoint triggers the `crud.populate_script_result_table` function to refresh the data in the script's dedicated staging table (`stg.dq_script_{id}`).
        *   **Note**: The `script_id` must correspond to an existing SQL script, and the request body should specify the database connection details if not using the default.
    *   `publish_results(script_id: int, ...)`: Mapped to `POST /{script_id}/publish`. This endpoint triggers the `crud.publish_script_results` function. It takes the data from the script's staging table (`stg.dq_script_{id}`) and merges it into the central `dq.bad_detail` table. For each unique `(rule_id, source_id)` pair, it deletes existing records before inserting the new ones.

### 4. `app/routes/bad_detail.py`

*   **Purpose**: Provides a user-friendly interface for filtering and viewing bad detail records.
*   **Key Components**:
    *   `app/routes/bad_detail.py`: Contains endpoints for retrieving and filtering bad detail data.
    *   `app/templates/bad_detail_query.html`: Frontend template with filtering UI and results display.
*   **Key Features**:
    *   Filtering by rule_id and source_id with descriptive dropdowns showing both ID and name
    *   Pagination for large result sets
    *   Integration with visualization tools

### 5. `app/routes/stats.py`

*   **Purpose**: Provides graphical representation of bad detail data for easier analysis.
*   **Key Components**:
    *   `app/routes/stats.py`: Contains endpoints for generating visualization data.
    *   `app/templates/visualization.html`: Frontend template with Chart.js visualizations.
*   **Key Features**:
    *   Bad detail counts by date (line chart)
    *   Bad detail counts by rule (bar chart)
    *   Bad detail counts by source (bar chart)
    *   Filtering by rule_id and source_id with descriptive dropdowns

### 6. `app/routes/scheduler.py`

*   **Purpose**: Allows scheduling SQL scripts to run at specific intervals.
*   **Key Components**:
    *   `app/routes/scheduler.py`: Contains endpoints for managing job schedules.
    *   `app/templates/scheduler.html`: Frontend interface for schedule management.
*   **Key Features**:
    *   Support for daily, weekly, and monthly schedules
    *   Cron-based scheduling (using standard cron format)
    *   Active/inactive status toggling
    *   Integration with SQL scripts

### 7. `app/routes/reference_tables.py`

*   **Purpose**: Provides an interface for managing rule and source reference tables.
*   **Key Components**:
    *   `app/routes/reference_tables.py`: Contains endpoints for CRUD operations on reference tables.
    *   `app/templates/reference_tables.html`: Frontend interface for managing references.
*   **Key Features**:
    *   Add, view, and delete rule references
    *   Add, view, and delete source references
    *   Integration with bad detail query and visualization for improved data display

### 8. `app/auth.py`

*   **Purpose**: Provides user authentication and authorization capabilities.
*   **Key Components**:
    *   `app/auth.py`: Core authentication logic.
    *   `app/dependencies_auth.py`: Authentication-related dependencies for routes.
    *   `app/routes/auth.py`: API routes for login, registration, and user management.
*   **Key Features**:
    *   JWT-based token authentication
    *   Password hashing for security
    *   Login/logout functionality
    *   User profile management

## Frontend (`app/static/`)

*   `index.html`: The main landing page for the application.
*   `sql_editor.html`: Provides a user interface for writing, saving, and executing SQL scripts. It now includes a "Populate" button for each saved script, which calls the `POST /{script_id}/populate_table` endpoint to refresh the data in its dedicated staging table. It also includes a "Publish" button to move the data from the staging table to the final `dq.bad_detail` table.
*   `bad_detail_query.html`: Frontend template for the bad detail query interface, allowing users to filter and view bad detail records.
*   `visualization.html`: Frontend template for data visualization, showing charts and graphs of bad detail data.
*   `scheduler.html`: Frontend interface for managing scheduled jobs for SQL scripts.
*   `reference_tables.html`: Frontend interface for managing rule and source reference tables.
*   `partials/`: Directory containing reusable template components, such as the navigation bar.

## Setup and Running

1.  **Environment Variables**: A `.env` file in the DQX root directory should define `DATABASE_URL` (e.g., `DATABASE_URL="postgresql://user:password@host:port/database"`).
2.  **Dependencies**: Install dependencies from `requirements.txt` (`pip install -r requirements.txt`).
3.  **Database Schema**: Before running the application, ensure the required `dq.dq_sql_scripts` table is created in your PostgreSQL database with the correct schema. The `id` column **must** be an auto-incrementing primary key.
    ```sql
    CREATE TABLE dq.dq_sql_scripts (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        description TEXT,
        content TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    -- It is also assumed that a `dq.bad_detail` table exists with a compatible structure.
    CREATE TABLE dq.bad_detail (
        rule_id VARCHAR(20),
        source_id VARCHAR(20),
        source_uid VARCHAR(500),
        data_value VARCHAR(2000),
        txn_date DATE,
        -- A composite primary key is recommended to ensure uniqueness
        -- and improve performance of delete operations.
        PRIMARY KEY (rule_id, source_id, source_uid) 
    );
    ```
4.  **Running**: Execute `python app/main.py` from the DQX root directory, or run using Uvicorn directly: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`.

## Key Design Considerations

*   **Database Interaction**: All database operations are now performed using `psycopg2` directly, offering fine-grained control over SQL and removing the SQLAlchemy ORM layer.
*   **SQL Safety**: `psycopg2.sql` module is used for constructing SQL queries with dynamic identifiers and placeholders, mitigating SQL injection risks.
*   **SQL Script Validation**: A strict validation (`_validate_sql_script_columns` in `crud.py`) is enforced for all saved and executed SQL scripts. They must be `SELECT` statements and output exactly five columns: `rule_id`, `source_id`, `source_uid`, `data_value`, and `txn_date`. This ensures data consistency for downstream processes.
*   **Unique Script Names**: The application now prevents the creation or renaming of SQL scripts to a name that is already in use, ensuring that every script has a unique identifier.
*   **Staging Table Automation**: For each validated SQL script, the application automatically manages a corresponding staging table in the `stg` schema. This allows the results of any script to be materialized into a persistent, queryable table that can be refreshed on demand.
*   **Publishing Workflow**: A two-step process allows for safe data validation. First, results are loaded into a temporary staging table using the "Populate" button. After verification, the "Publish" button merges these results into the final `dq.bad_detail` table. The merge logic is idempotent based on `(rule_id, source_id)` pairs, providing a controlled and reliable way to update production data quality records.
*   **Separation of Concerns**: The project maintains a structure with separate modules for database connection (`database.py`), data schemas (`schemas.py`), CRUD operations (`crud.py`), and API routing (`routes/`).
*   **Error Handling**: Global exception handling in `main.py` ensures that all unhandled backend errors return a JSON response. Frontend JavaScript in all templates includes robust error handling for API calls.
*   **Scheduler**: Users can schedule SQL scripts to run at daily, weekly, or monthly intervals. This is managed through a dedicated scheduler UI and a set of API endpoints. Job scheduling uses cron expressions for flexibility.
*   **Reference Data Integration**: Rule and source reference tables are integrated throughout the application, providing human-readable names alongside IDs for better usability.
*   **Visualization Dashboard**: The application includes a dashboard with Chart.js visualizations to help users analyze data quality issues over time and across different rules and sources.
*   **Modern UI**: The frontend uses Bootstrap and custom CSS with responsive design for a consistent and modern look and feel across all pages. The navigation bar is optimized for both desktop and mobile devices.

## Utilities

The `utils` directory contains several utility modules that provide additional functionality:

### Chat Logging (logger.py)

The `logger.py` module provides comprehensive chat logging capabilities:

*   **Core Functions**:
    *   `log_chat(user_message, assistant_response, custom_timestamp=None)`: Records conversations between users and assistants with timestamps.
    *   `read_chat_logs(num_entries=None, from_date=None)`: Retrieves and parses logs from the log file with filtering options.
    *   `clear_chat_logs()`: Removes all logs by deleting the log file.
    *   `get_chat_log_path()`: Returns the absolute path to the chat log file.

*   **Features**:
    *   Custom timestamps for backdating logs
    *   Structured format with clear separation between conversations
    *   Filtering logs by date or limiting to recent entries
    *   Error handling to ensure logging stability

*   **Integration Points**:
    *   Web UI (`/references`) for rule and source reference tables management
    *   Direct database access via SQL for advanced integrations
    *   Browser-based interface for viewing, adding and deleting reference data

*   **Example Usage**:
    ```python
    # Import the logging function
    from utils.logger import log_chat
    
    # Log a conversation
    log_chat(
        user_message="How do I execute a SQL query?",
        assistant_response="You can use the SQL Editor at /editor"
    )
    
    # Read and process logs
    from utils.logger import read_chat_logs
    from datetime import datetime, timedelta
    
    # Get logs from the past week
    one_week_ago = datetime.now() - timedelta(days=7)
    recent_logs = read_chat_logs(from_date=one_week_ago)
    
    # Process the logs
    for log in recent_logs:
        print(f"[{log['timestamp']}] User: {log['user']}")
    ```

For more examples, see the `utils/logger_examples.py` file.

## New Features

### 1. Bad Detail Query

*   **Purpose**: Provides a user-friendly interface for filtering and viewing bad detail records.
*   **Key Components**:
    *   `app/routes/bad_detail.py`: Contains endpoints for retrieving and filtering bad detail data.
    *   `app/templates/bad_detail_query.html`: Frontend template with filtering UI and results display.
*   **Key Features**:
    *   Filtering by rule_id and source_id with descriptive dropdowns showing both ID and name
    *   Pagination for large result sets
    *   Integration with visualization tools

### 2. Data Visualization

*   **Purpose**: Provides graphical representation of bad detail data for easier analysis.
*   **Key Components**:
    *   `app/routes/stats.py`: Contains endpoints for generating visualization data.
    *   `app/templates/visualization.html`: Frontend template with Chart.js visualizations.
*   **Key Features**:
    *   Bad detail counts by date (line chart)
    *   Bad detail counts by rule (bar chart)
    *   Bad detail counts by source (bar chart)
    *   Filtering by rule_id and source_id with descriptive dropdowns

### 3. Job Scheduler

*   **Purpose**: Allows scheduling SQL scripts to run at specific intervals.
*   **Key Components**:
    *   `app/routes/scheduler.py`: Contains endpoints for managing job schedules.
    *   `app/templates/scheduler.html`: Frontend interface for schedule management.
*   **Key Features**:
    *   Support for daily, weekly, and monthly schedules
    *   Cron-based scheduling (using standard cron format)
    *   Active/inactive status toggling
    *   Integration with SQL scripts

### 4. Reference Tables Management

*   **Purpose**: Provides an interface for managing rule and source reference tables.
*   **Key Components**:
    *   `app/routes/reference_tables.py`: Contains endpoints for CRUD operations on reference tables.
    *   `app/templates/reference_tables.html`: Frontend interface for managing references.
*   **Key Features**:
    *   Add, view, and delete rule references
    *   Add, view, and delete source references
    *   Integration with bad detail query and visualization for improved data display

### 5. Authentication and Authorization

*   **Purpose**: Provides user authentication and authorization capabilities.
*   **Key Components**:
    *   `app/auth.py`: Core authentication logic.
    *   `app/dependencies_auth.py`: Authentication-related dependencies for routes.
    *   `app/routes/auth.py`: API routes for login, registration, and user management.
*   **Key Features**:
    *   JWT-based token authentication
    *   Password hashing for security
    *   Login/logout functionality
    *   User profile management

### 6. Improved Navigation and UI

*   **Purpose**: Enhances user experience with a consistent and responsive design.
*   **Key Components**:
    *   `app/static/css/style.css`: Shared CSS styles.
    *   `app/templates/partials/main_nav.html`: Reusable navigation component.
*   **Key Features**:
    *   Responsive navigation bar with mobile support
    *   Consistent styling across all pages
    *   Improved typography and spacing
    *   Visual indicators for active page

## Database Schema

### Key Tables

1. **dq.bad_detail**
   ```sql
   CREATE TABLE dq.bad_detail (
       rule_id VARCHAR(20),
       source_id VARCHAR(20),
       source_uid VARCHAR(500),
       data_value VARCHAR(2000),
       txn_date DATE,
       PRIMARY KEY (rule_id, source_id, source_uid)
   );
   ```

2. **dq.rule_ref**
   ```sql
   CREATE TABLE dq.rule_ref (
       rule_id VARCHAR(20) PRIMARY KEY,
       rule_name VARCHAR(100) NOT NULL,
       description TEXT
   );
   ```

3. **dq.source_ref**
   ```sql
   CREATE TABLE dq.source_ref (
       source_id VARCHAR(20) PRIMARY KEY,
       source_name VARCHAR(100) NOT NULL,
       description TEXT
   );
   ```

4. **dq.dq_schedules**
   ```sql
   CREATE TABLE dq.dq_schedules (
       id SERIAL PRIMARY KEY,
       job_name VARCHAR(100) NOT NULL,
       script_id INTEGER REFERENCES dq.dq_sql_scripts(id) ON DELETE CASCADE,
       cron_schedule VARCHAR(100) NOT NULL,
       is_active BOOLEAN DEFAULT TRUE,
       created_at TIMESTAMPTZ DEFAULT NOW(),
       updated_at TIMESTAMPTZ DEFAULT NOW()
   );
   ```

5. **dq.users**
   ```sql
   CREATE TABLE dq.users (
       id SERIAL PRIMARY KEY,
       username VARCHAR(50) UNIQUE NOT NULL,
       email VARCHAR(100) UNIQUE NOT NULL,
       hashed_password VARCHAR(100) NOT NULL,
       is_active BOOLEAN DEFAULT TRUE,
       is_admin BOOLEAN DEFAULT FALSE,
       created_at TIMESTAMPTZ DEFAULT NOW()
   );
   ```
