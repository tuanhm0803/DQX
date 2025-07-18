# DQX Project Documentation

## Overview

DQX is a FastAPI application designed to provide a web-based interface for interacting with multiple PostgreSQL databases using `psycopg2`. It implements a **target/source database architecture** where users can create tables in a single target database (localhost:5432) while querying data from multiple source databases. The application has been built from the ground up to use pure PostgreSQL with `psycopg2` for all direct database interactions, enhancing control over SQL execution and simplifying the database layer.

## Multi-Database Architecture

*   **Purpose**: Provides a multi-database interface for creating and managing tables in the target database using data from source databases.
*   **Key Components**:
    *   `app/routes/source_data_management.py`: Contains endpoints for multi-database table operations.
    *   `app/templates/source_data_management.html`: Frontend interface with target/source database distinction.
*   **Architecture**:
    *   **Target Database**: Single database (localhost:5432) where all tables are created in the `stg` schema
    *   **Source Databases**: Multiple databases that can be queried for data but where no tables are created
    *   **Cross-Database Queries**: SQL scripts can reference data from multiple source databases
*   **Key Features**:
    *   **Target Database Management**: 
        - View target database connection status
        - Automatic `stg` schema creation if it doesn't exist
        - All table creation operations happen only in target database
    *   **Source Database Discovery**:
        - Display all configured source databases
        - Test connectivity to source databases
        - Browse schemas and tables in source databases
    *   **Multi-Database Table Creation**:
        - Create tables in target database using data from source databases
        - SQL editor with syntax highlighting using CodeMirror
        - Cross-database query examples and guidance
    *   **Table Management** (Target Database Only):
        - Insert data into existing stg tables
        - Truncate tables to quickly remove all data
        - Drop tables to completely remove them
        - View table data with a modal display
    *   **Security Features**:
        - Table name validation for security
        - Target database enforcement (no table creation in source databases)
        - Connection testing and error handling
*   **Key Endpoints**:
    *   `GET /source_data_management`: Main interface showing target and source databases
    *   `POST /source_data_management/create_table`: Create table in target database only
    *   `POST /source_data_management/insert_data`: Insert data into target database table
    *   `POST /source_data_management/truncate_table`: Truncate target database table
    *   `POST /source_data_management/drop_table`: Drop target database table
    *   `GET /api/database_connections`: List all configured database connections
    *   `POST /api/database_connections/{conn_id}/test`: Test specific database connectionactions, enhancing control over SQL execution and simplifying the database layer.

## Multi-Database Architecture

### Target Database
- **Location**: localhost:5432 (your working database)
- **Purpose**: Where all new tables are created in the `stg` schema
- **Operations**: Full CRUD operations (CREATE, READ, UPDATE, DELETE)
- **Access**: Primary database for all table management operations

### Source Databases
- **Location**: Remote PostgreSQL servers (configured in .env)
- **Purpose**: External databases containing source data
- **Operations**: READ-ONLY queries for data extraction
- **Access**: Query permissions only for pulling data

### Multi-Database Workflow
1. **Configuration**: Define target and source databases in `.env` file
2. **Connection Management**: Multi-database manager handles all connections
3. **Data Extraction**: Query source databases to identify available data
4. **Table Creation**: Create tables in target database using data from source databases
5. **Data Management**: Manage tables (insert, truncate, drop) in target database only

## Project Structure

```
DQX/
├── README.md
├── DOCUMENTATION.md
├── requirements.txt
├── .env                    # Database connection configuration
├── .env.example            # Example configuration file
├── app/
│   ├── __init__.py
│   ├── crud.py             # Core database interaction logic (Create, Read, Update, Delete) using psycopg2
│   ├── database.py         # Primary database connection management using psycopg2
│   ├── multi_db_manager.py # Multi-database connection manager for target/source databases
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
│   │   ├── source_data_management.py # Multi-database routes for table management
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
│       ├── source_data_management.html # Multi-database table management interface
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

*   **Purpose**: Allows scheduling SQL scripts to run at specific intervals with optional auto-publishing.
*   **Key Components**:
    *   `app/routes/scheduler.py`: Contains endpoints for managing job schedules.
    *   `app/templates/scheduler.html`: Frontend interface for schedule management.
*   **Key Features**:
    *   Support for daily, weekly, and monthly schedules
    *   Cron-based scheduling (using standard cron format)
    *   Active/inactive status toggling
    *   **Auto-Publish Results**: Schedules can automatically publish results to the central `dq.bad_detail` table after execution
    *   Integration with SQL scripts
*   **Auto-Publish Feature**:
    *   Added `auto_publish` BOOLEAN column to `dq.dq_schedules` table
    *   When enabled, script results are automatically moved from staging tables (`stg.dq_script_{id}`) to `dq.bad_detail`
    *   Eliminates manual publishing step for automated workflows
    *   Configurable per schedule with checkbox in UI
    *   Backward compatible (defaults to FALSE for existing schedules)

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

### 1. Environment Configuration
Create a `.env` file in the DQX root directory with the following structure:

#### New Individual Parameter Format (Recommended)
```bash
# DQX Database Configuration

# Database Type: postgresql or oracle
DB_TYPE=postgresql

# Database Connection Parameters
DB_HOST=localhost
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=123456

# Target database - where tables will be created (your working database)
TARGET_DB_NAME=Working Database
TARGET_DB_HOST=localhost
TARGET_DB_PORT=5432
TARGET_DB_NAME_DB=postgres
TARGET_DB_USER=postgres
TARGET_DB_PASSWORD=123456
TARGET_DB_DESC=Primary working database where tables are created

# Source databases - where data will be queried from (these should be different from your target database)
DB_SOURCE_PROD_NAME=Production Database
DB_SOURCE_PROD_HOST=prod-server
DB_SOURCE_PROD_PORT=5432
DB_SOURCE_PROD_NAME_DB=prod_db
DB_SOURCE_PROD_USER=prod_user
DB_SOURCE_PROD_PASSWORD=prod_password
DB_SOURCE_PROD_DESC=Production database (source data)

DB_SOURCE_STAGING_NAME=Staging Environment
DB_SOURCE_STAGING_HOST=staging-server
DB_SOURCE_STAGING_PORT=5432
DB_SOURCE_STAGING_NAME_DB=staging_db
DB_SOURCE_STAGING_USER=staging_user
DB_SOURCE_STAGING_PASSWORD=staging_password
DB_SOURCE_STAGING_DESC=Staging database (source data)
```

#### Legacy URL Format (Still Supported)
```bash
# Primary database connection (for authentication and core app operations)
DATABASE_URL=postgresql://postgres:password@localhost:5432/postgres

# Target database - where tables will be created (your working database)
TARGET_DB_NAME=Working Database
TARGET_DB_URL=postgresql://postgres:password@localhost:5432/postgres
TARGET_DB_DESC=Primary working database where tables are created

# Source databases - where data will be queried from
DB_SOURCE_PROD_URL=postgresql://prod_user:prod_password@prod-server:5432/prod_db
DB_SOURCE_PROD_DESC=Production database (source data)

# Add more source databases as needed following the pattern:
# DB_SOURCE_<ID>_NAME, DB_SOURCE_<ID>_URL, DB_SOURCE_<ID>_DESC

# JWT Configuration
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

### 2. Dependencies
Install Python dependencies:
```bash
pip install -r requirements.txt
```

### 3. Database Schema Setup
Before running the application, ensure the required database schema is created in your **target database**:

```sql
-- Create main DQ schema for data quality tables
CREATE SCHEMA IF NOT EXISTS dq;

-- Create users table for authentication
CREATE TABLE IF NOT EXISTS dq.users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    full_name VARCHAR(100),
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    role VARCHAR(20) NOT NULL DEFAULT 'inputter',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT users_role_check CHECK (role IN ('admin', 'creator', 'inputter'))
);

-- Create STG schema for table creation
CREATE SCHEMA IF NOT EXISTS stg;

-- Create SQL scripts table
CREATE TABLE IF NOT EXISTS dq.sql_scripts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(50),
    updated_by VARCHAR(50)
);

-- Create scheduled jobs table
CREATE TABLE IF NOT EXISTS dq.scheduled_jobs (
    id SERIAL PRIMARY KEY,
    script_id INTEGER REFERENCES dq.sql_scripts(id) ON DELETE CASCADE,
    schedule_type VARCHAR(20) NOT NULL CHECK (schedule_type IN ('daily', 'weekly', 'monthly')),
    schedule_time TIME NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    last_run TIMESTAMPTZ,
    next_run TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(50)
);

-- Create bad detail table for data quality results
CREATE TABLE IF NOT EXISTS dq.bad_detail (
    id SERIAL PRIMARY KEY,
    rule_id INTEGER NOT NULL,
    source_id INTEGER NOT NULL,
    source_uid VARCHAR(255) NOT NULL,
    data_value TEXT,
    txn_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(rule_id, source_id, source_uid)
);

-- Create reference tables for rules and sources
CREATE TABLE IF NOT EXISTS dq.rule_reference (
    rule_id INTEGER PRIMARY KEY,
    rule_name VARCHAR(255) NOT NULL,
    rule_description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS dq.source_reference (
    source_id INTEGER PRIMARY KEY,
    source_name VARCHAR(255) NOT NULL,
    source_description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create user actions log table (timezone-free for Oracle compatibility)
CREATE TABLE IF NOT EXISTS dq.user_actions_log (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(100),
    details TEXT,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create schedule run log table (timezone-free for Oracle compatibility)
CREATE TABLE IF NOT EXISTS dq.schedule_run_log (
    id SERIAL PRIMARY KEY,
    schedule_id INTEGER REFERENCES dq.scheduled_jobs(id) ON DELETE CASCADE,
    script_id INTEGER NOT NULL,
    script_name VARCHAR(255),
    status VARCHAR(20) NOT NULL CHECK (status IN ('success', 'error', 'running')),
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    rows_affected INTEGER,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_user_actions_log_username ON dq.user_actions_log(username);
CREATE INDEX IF NOT EXISTS idx_user_actions_log_created_at ON dq.user_actions_log(created_at);
CREATE INDEX IF NOT EXISTS idx_schedule_run_log_schedule_id ON dq.schedule_run_log(schedule_id);
CREATE INDEX IF NOT EXISTS idx_schedule_run_log_created_at ON dq.schedule_run_log(created_at);
CREATE INDEX IF NOT EXISTS idx_bad_detail_rule_source ON dq.bad_detail(rule_id, source_id);
```

**Important Schema Notes:**

1. **Role-Based Security Tables**: 
   - `dq.users` table with role-based access control (admin, creator, inputter)
   - Role constraints ensure data integrity

2. **Audit and Logging Tables**:
   - `dq.user_actions_log` tracks all user actions for security auditing
   - `dq.schedule_run_log` tracks scheduled job executions
   - **Timezone-free**: Uses `TIMESTAMP` (no timezone) for Oracle database compatibility

3. **Core Application Tables**:
   - `dq.sql_scripts` stores user-created SQL scripts with metadata
   - `dq.scheduled_jobs` manages automated script execution
   - `dq.bad_detail` stores data quality results
   - `dq.rule_reference` and `dq.source_reference` provide lookup data

4. **Schema Organization**:
   - `dq` schema: Core application data and logs
   - `stg` schema: Staging tables for temporary data processing

5. **Performance Optimization**:
   - Indexes on frequently queried columns
   - Foreign key constraints for data integrity
   - Unique constraints to prevent duplicates

6. **Oracle Compatibility**:
   - All datetime fields in log tables use `TIMESTAMP` without timezone
   - Schema designed to work with both PostgreSQL and Oracle databases

### 4. Source Database Setup
For each source database you want to connect to:
1. Ensure the user specified in your `.env` file has READ permissions
2. Grant necessary schema and table access permissions
3. Test connectivity using the application's connection test feature

### 5. Running the Application
Execute from the DQX root directory:
```bash
# Using Python directly
python -m app.main

# Using Uvicorn (recommended for development)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# For production
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 6. Initial Setup
1. Access the application at `http://localhost:8000`
2. Register the first admin user
3. Configure additional database connections in the Source Data Management section
4. Test all database connections before creating tables

## API Reference

## Key Design Considerations

*   **Database Interaction**: All database operations are performed using `psycopg2` directly, offering fine-grained control over SQL and removing the SQLAlchemy ORM layer.
*   **SQL Safety**: `psycopg2.sql` module is used for constructing SQL queries with dynamic identifiers and placeholders, mitigating SQL injection risks.
*   **Role-Based Security**: Comprehensive permission system with three user roles (admin, creator, inputter) and function-level access control.
*   **Simplified Permissions**: Consolidated permission functions reduce code complexity while maintaining security:
    - `can_admin_creator_access()` replaces six individual permission functions
    - Clear separation between admin-only and admin/creator features
    - Inputter role restrictions are enforced at both backend and frontend levels
*   **Audit and Compliance**: 
    - All user actions are automatically logged to `dq.user_actions_log`
    - Schedule job runs are tracked in `dq.schedule_run_log` 
    - Timezone-free logging for Oracle database compatibility
*   **Database Flexibility**: 
    - Individual parameter configuration supports easy database switching
    - Oracle database support prepared (PostgreSQL to Oracle migration ready)
    - Backward compatibility with legacy URL-based configuration
*   **SQL Script Validation**: A strict validation (`_validate_sql_script_columns` in `crud.py`) is enforced for all saved and executed SQL scripts. They must be `SELECT` statements and output exactly five columns: `rule_id`, `source_id`, `source_uid`, `data_value`, and `txn_date`. This ensures data consistency for downstream processes.
*   **Unique Script Names**: The application prevents the creation or renaming of SQL scripts to a name that is already in use, ensuring that every script has a unique identifier.
*   **Staging Table Automation**: For each validated SQL script, the application automatically manages a corresponding staging table in the `stg` schema. This allows the results of any script to be materialized into a persistent, queryable table that can be refreshed on demand.
*   **Publishing Workflow**: A two-step process allows for safe data validation. First, results are loaded into a temporary staging table using the "Populate" button. After verification, the "Publish" button merges these results into the final `dq.bad_detail` table. The merge logic is idempotent based on `(rule_id, source_id)` pairs, providing a controlled and reliable way to update production data quality records.
*   **Separation of Concerns**: The project maintains a structure with separate modules for database connection (`database.py`), data schemas (`schemas.py`), CRUD operations (`crud.py`), and API routing (`routes/`).
*   **Error Handling**: Global exception handling in `main.py` ensures that all unhandled backend errors return a JSON response. Frontend JavaScript in all templates includes robust error handling for API calls.
*   **Scheduler**: Users can schedule SQL scripts to run at daily, weekly, or monthly intervals. This is managed through a dedicated scheduler UI and a set of API endpoints. Job scheduling uses cron expressions for flexibility.
*   **Reference Data Integration**: Rule and source reference tables are integrated throughout the application, providing human-readable names alongside IDs for better usability.
*   **Visualization Dashboard**: The application includes a dashboard with Chart.js visualizations to help users analyze data quality issues over time and across different rules and sources.
*   **Modern UI**: The frontend uses Bootstrap and custom CSS with responsive design for a consistent and modern look and feel across all pages. The navigation bar is optimized for both desktop and mobile devices.

## Recent Updates and Features

### User Action Logging
- **Automatic Logging**: All user actions are automatically tracked via middleware
- **Audit Trail**: Complete history of who did what and when
- **Log Viewer**: Admin and creator users can view logs via `/user-actions-log` page
- **Filtering**: Filter logs by username, action type, resource type, and date range
- **Security**: Inputter users cannot view action logs

### Schedule Run Logging  
- **Job Tracking**: All scheduled job executions are logged with status and timing
- **Error Capture**: Failed jobs include detailed error messages
- **Performance Metrics**: Track execution time and rows affected
- **Integration**: Schedule logs are visible in the scheduler interface

### Simplified Role Permissions
- **Consolidated Functions**: Reduced from 6 permission functions to 3 main functions
- **Clear Access Control**: 
  - Admin: Full access including user management
  - Creator: Data operations but no user management  
  - Inputter: Read-only access, cannot modify data
- **Frontend Integration**: Role restrictions enforced in templates and navigation

### Oracle Database Preparation
- **Configuration Ready**: Individual parameter format supports Oracle connections
- **Timezone Compatibility**: All log tables use timezone-free timestamps
- **Schema Compatibility**: Database schema designed for cross-platform support
- **Migration Path**: Clear upgrade path from PostgreSQL to Oracle

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

### 5. Authentication and Role-Based Authorization

*   **Purpose**: Provides user authentication and role-based access control.
*   **Key Components**:
    *   `app/auth.py`: Core authentication logic.
    *   `app/dependencies_auth.py`: Authentication-related dependencies for routes.
    *   `app/routes/auth.py`: API routes for login and user management.
    *   `app/role_permissions.py`: Role-based access control functions.
    *   `app/routes/admin.py`: Admin user management routes.
    *   `app/templates/admin/user_management.html`: User management interface.
*   **Key Features**:
    *   JWT-based token authentication
    *   Password hashing for security
    *   Role-based access control with three roles:
        *   **Admin**: Full access to all features including user management
        *   **Creator**: Can create tables and insert data, but cannot manage users
        *   **Inputter**: Read-only access, cannot create tables or insert data
    *   Login/logout functionality
    *   User profile management
    *   Admin user management interface
    *   Session timeout after 1 hour of inactivity
    *   Session protection for all pages except the main landing page
    *   Automatic login modal popup for expired sessions or unauthenticated users
    *   Middleware-based authentication verification for all protected routes

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

### 7. Source Data Management

*   **Purpose**: Provides an interface for managing tables in the stg schema through SQL.
*   **Key Components**:
    *   `app/routes/source_data_management.py`: Contains endpoints for table operations in the stg schema.
    *   `app/templates/source_data_management.html`: Frontend interface with tabbed UI for different operations.
*   **Key Features**:
    *   Create tables in the stg schema using SQL scripts
    *   Insert data into existing stg tables
    *   Truncate tables to quickly remove all data
    *   Drop tables to completely remove them
    *   View table data with a modal display
    *   SQL editor with syntax highlighting using CodeMirror
    *   Table name validation for security

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
       auto_publish BOOLEAN NOT NULL DEFAULT FALSE,
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
       full_name VARCHAR(100),
       hashed_password VARCHAR(255) NOT NULL,
       is_active BOOLEAN DEFAULT TRUE,
       role VARCHAR(20) NOT NULL DEFAULT 'inputter',
       created_at TIMESTAMPTZ DEFAULT NOW(),
       updated_at TIMESTAMPTZ DEFAULT NOW(),
       CONSTRAINT users_role_check CHECK (role IN ('admin', 'creator', 'inputter'))
   );
   ```

#### Oracle Database Support
To switch to Oracle database, simply change the database type and connection parameters:
```bash
# Database Type: oracle
DB_TYPE=oracle
DB_HOST=oracle-server
DB_PORT=1521
DB_NAME=ORCL
DB_USER=dqx_user
DB_PASSWORD=dqx_password
```

**Note**: Oracle support requires additional setup:
- Install Oracle Instant Client
- Install `cx_Oracle` or `oracledb` Python package
- Update connection logic in `app/database.py` (currently prepared but not fully implemented)

#### Configuration Benefits
The new individual parameter format provides several advantages:

1. **Database Flexibility**: Easy switching between PostgreSQL and Oracle
2. **Clear Configuration**: Individual parameters are more readable than URL strings
3. **Environment Specific**: Easy to override individual parameters for different environments
4. **Future Ready**: Prepared for Oracle integration when needed
5. **Backward Compatible**: Still supports legacy URL format

### 2. Role-Based Access Control

The application implements a simplified role-based permission system:

#### User Roles
- **Admin**: Full access to all functionality including user management
- **Creator**: Can create, modify, and delete data but cannot manage users
- **Inputter**: Read-only access, cannot create/modify/delete data or access advanced features

#### Permission Functions
The application uses a consolidated permission system:

- **`check_admin_access()`**: Admin-only access (user management)
- **`check_creator_access()`**: Admin and Creator access (general operations)
- **`can_publish_populate()`**: Admin and Creator access (script publishing)
- **`can_manage_users()`**: Admin-only access (user management)
- **`can_admin_creator_access()`**: Admin and Creator access (consolidated function for):
  - Create tables
  - Insert data
  - Access source data management
  - Delete scripts
  - Delete scheduled jobs
  - View action logs

#### Restricted Features for Inputters
Inputters are blocked from:
- Publishing and populating scripts in DQ Scripts page
- Accessing Source Data Management page
- Creating or modifying tables
- Deleting scripts or scheduled jobs
- Viewing user action logs
- Managing users
