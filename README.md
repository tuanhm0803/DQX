# DQX - Database Query Explorer

A FastAPI application for exploring and querying databases with multi-database support and a web interface.

## Multi-Database Architecture

DQX now supports a **target/source database architecture**:

- **Target Database**: A single PostgreSQL database (localhost:5432) where all new tables are created in the `stg` schema
- **Source Databases**: Multiple PostgreSQL databases that can be queried for data but where no tables are created
- **Cross-Database Queries**: SQL scripts can reference data from multiple source databases to create tables in the target database

### Database Configuration

Configure your databases in the `.env` file:

```bash
# Target database - where tables will be created (your working database)
TARGET_DB_NAME=Working Database
TARGET_DB_URL=postgresql://postgres:password@localhost:5432/postgres
TARGET_DB_DESC=Primary working database where tables are created

# Source databases - where data will be queried from
DB_SOURCE_PROD_NAME=Production Database
DB_SOURCE_PROD_URL=postgresql://prod_user:prod_password@prod-server:5432/prod_db
DB_SOURCE_PROD_DESC=Production database (source data)

DB_SOURCE_STAGING_NAME=Staging Environment
DB_SOURCE_STAGING_URL=postgresql://staging_user:staging_password@staging-server:5432/staging_db
DB_SOURCE_STAGING_DESC=Staging environment database (source data)
```

## Advanced Features

- **Multi-Database Source Data Management**: Create tables in your target database using data from multiple source databases
- **Data Quality Management**: Manage rule and source references through the UI
- **Bad Detail Query**: Filter and view bad detail records with pagination
- **Visualizations**: Graphical representation of bad details data
- **Job Scheduling**: Schedule SQL scripts using daily, weekly, or monthly patterns
- **User Management**: Role-based authentication (admin, creator, inputter roles)
- **Security**: 
  - Session timeout after 1 hour of inactivity
  - Automatic login modal for expired sessions
  - All pages protected by authentication except the main page

## Features

- **Multi-Database Support**: Connect to multiple PostgreSQL databases as source systems
- **Target Database Management**: All table creation happens in a single target database (localhost:5432)
- **Cross-Database Queries**: Write SQL scripts that pull data from multiple source databases
- **Table Operations**: Create, insert data into, truncate, and drop tables in the stg schema
- Execute SQL queries across multiple databases
- Save and manage SQL scripts
- Schedule SQL scripts to run at specific intervals using cron schedules
- Web interface for interacting with databases
- Data quality validation with rule and source reference tables
- Bad detail query and visualization tools
- Improved navigation with responsive design

## Installation

1. Clone this repository
2. Install dependencies: `pip install -r requirements.txt`
3. Configure your database connections in `.env` file (see example above)
4. Run the application: `python -m app.main`

## Source Data Management

The **Source Data Management** feature allows you to:

1. **View Target Database**: See your working database where all tables will be created
2. **View Source Databases**: See all configured source databases available for querying
3. **Create Tables**: Create new tables in the target database's `stg` schema using data from source databases
4. **Manage Data**: Insert, truncate, or drop tables in the target database
5. **Cross-Database Queries**: Write SQL that references multiple source databases

### Example Usage

```sql
-- Create a table in target database using data from multiple sources
SELECT 
    p.product_id,
    p.product_name,
    s.sales_amount,
    a.analytics_score
FROM production_db.products p
JOIN staging_db.sales s ON p.product_id = s.product_id
LEFT JOIN analytics_db.scores a ON p.product_id = a.product_id
WHERE p.created_date >= '2024-01-01'
```

This SQL would create a table in your target database's `stg` schema by pulling data from three different source databases.

## Reference Tables

The application includes reference tables management for rules and sources. Access this functionality via the UI at `/references`, where you can:

1. **View**: See all existing rule and source reference records
2. **Add**: Create new rule and source reference records with forms
3. **Delete**: Remove existing rule and source reference records as needed

### User Roles

The application implements role-based access control with the following roles:

1. **Admin** - Full access to all features including user management
2. **Creator** - Can create tables and insert data, but cannot manage users
3. **Inputter** - Read-only access, cannot create tables or insert data

### Advanced Features

- **Data Quality Management**: Manage rule and source references through the UI
- **Bad Detail Query**: Filter and view bad detail records with pagination
- **Visualizations**: Graphical representation of bad details data
- **Job Scheduling**: Schedule SQL scripts using daily, weekly, or monthly patterns
- **User Management**: Authentication and role-based access control

### Database Structure

The application uses PostgreSQL with the following key tables:

1. **dq.bad_detail** - Stores data quality validation errors
2. **dq.rule_ref** - Reference table for data quality rules
3. **dq.source_ref** - Reference table for data sources
4. **dq.dq_schedules** - Stores job scheduling information
5. **dq.dq_sql_scripts** - Stores saved SQL scripts

### Key Pages

- **/** - Home page with links to all functionality
- **/source_data_management** - Multi-database interface for managing tables (create tables in target DB using source DBs)
- **/admin/users** - User management interface (admin only)
- **/schedules** - Job scheduler interface
- **/references** - Rule and source reference tables management
- **/bad_detail_query** - Query interface for bad detail records
- **/visualization** - Data visualization dashboard

## Database Architecture Details

### Target Database (localhost:5432)
- **Purpose**: Your working database where all new tables are created
- **Schema**: Tables are created in the `stg` schema
- **Operations**: CREATE, INSERT, UPDATE, DELETE, TRUNCATE, DROP operations
- **Access**: Full read/write access

### Source Databases (Remote/External)
- **Purpose**: External databases that contain source data
- **Operations**: READ-ONLY queries for data extraction
- **Access**: Query permissions only
- **Usage**: Referenced in SQL scripts to pull data into target database

### Multi-Database Workflow
1. Configure source databases in `.env` file
2. Connect to source databases to explore available data
3. Write SQL scripts that query source databases
4. Create tables in target database using source data
5. Manage tables (insert, truncate, drop) in target database only

## Technologies Used

- FastAPI - Web framework for building APIs
- psycopg2 - PostgreSQL adapter for Python
- uvicorn - ASGI server for FastAPI
- Bootstrap - Frontend UI framework
- Chart.js - JavaScript charting library for visualizations
- HTML/CSS/JavaScript - Frontend technologies
