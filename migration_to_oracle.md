# PostgreSQL to Oracle Migration Guide

This document outlines the changes needed to migrate the DQX application from PostgreSQL with psycopg2 to Oracle using oracledb.

## Main Changes Required

### 1. Database Connection (`app/database.py`)
- Replace `psycopg2` with `oracledb`
- Update connection string format
- Modify connection parameters
- Update cursor handling

### 2. SQL Syntax Changes
- PostgreSQL specific functions to Oracle functions
- Schema references (PostgreSQL uses `schema.table`, Oracle uses `schema.table` or `schema_name.table_name`)
- Case sensitivity (Oracle identifiers are case-sensitive when quoted)
- Date/time handling differences
- Pagination syntax changes (LIMIT/OFFSET vs. ROWNUM)
- Sequence handling for auto-increment values

### 3. Data Type Mapping
- PostgreSQL `SERIAL` to Oracle `NUMBER` with sequences
- Boolean values (PostgreSQL boolean vs. Oracle NUMBER(1))
- TIMESTAMPTZ handling
- TEXT vs. CLOB/VARCHAR2

### 4. Transaction Management
- Autocommit behavior differences
- Exception handling for database operations

## Detailed Change List

### Install Required Package
```bash
pip install oracledb
pip freeze > requirements.txt
```

## Files That Need Modification

The following files need to be updated for the migration:
