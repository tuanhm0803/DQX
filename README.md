# DQX - Database Query Explorer

A FastAPI application for exploring and querying databases with a web interface.

## Advanced Features

- **Data Quality Management**: Manage rule and source references through the UI
- **Source Data Management**: Create, insert data into, truncate, and drop tables in the stg schema
- **Bad Detail Query**: Filter and view bad detail records with pagination
- **Visualizations**: Graphical representation of bad details data
- **Job Scheduling**: Schedule SQL scripts using daily, weekly, or monthly patterns
- **User Management**: Role-based authentication (admin, creator, inputter roles)

## Features

- Browse database tables
- Execute SQL queries
- Save and manage SQL scripts
- Schedule SQL scripts to run at specific intervals using cron schedules
- Web interface for interacting with databases
- Data quality validation with rule and source reference tables
- Bad detail query and visualization tools
- Improved navigation with responsive design

## Installation

1. Clone this repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run the application: `python -m app.main`

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
- **/source_data_management** - Interface for managing tables in the stg schema
- **/admin/users** - User management interface (admin only)
- **/schedules** - Job scheduler interface
- **/references** - Rule and source reference tables management
- **/bad_detail_query** - Query interface for bad detail records
- **/visualization** - Data visualization dashboard

## Technologies Used

- FastAPI - Web framework for building APIs
- psycopg2 - PostgreSQL adapter for Python
- uvicorn - ASGI server for FastAPI
- Bootstrap - Frontend UI framework
- Chart.js - JavaScript charting library for visualizations
- HTML/CSS/JavaScript - Frontend technologies
