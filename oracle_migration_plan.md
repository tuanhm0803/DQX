# PostgreSQL to Oracle Migration - Implementation Plan

This file provides a step-by-step implementation plan for migrating the DQX application from PostgreSQL to Oracle.

## Prerequisites

1. Install Oracle client libraries
2. Install Python oracledb package:
   ```
   pip install oracledb
   ```

## Implementation Steps

### 1. Database Connection Setup

1. Update `database.py` to use oracledb instead of psycopg2
2. Configure the proper Oracle connection parameters
3. Test connection to Oracle database

### 2. Database Schema Migration

1. Create schemas/users in Oracle
2. Convert PostgreSQL table creation scripts to Oracle format
3. Create sequences and triggers for ID generation (replacing SERIAL)
4. Migrate reference data to Oracle

### 3. Update Database Access Logic

1. Update parameter binding syntax (%s → :1 or :name)
2. Replace RETURNING clauses with Oracle equivalents 
3. Update pagination queries (LIMIT/OFFSET → ROW_NUMBER or OFFSET/FETCH)
4. Modify information_schema queries to use Oracle catalog views
5. Update cursor handling and result processing

### 4. Specific Component Updates

1. Authentication system (users table, login process)
2. Query execution and result handling
3. Table management in source_data_management routes
4. Bad detail query functionality
5. Scheduler functionality
6. Visualization data retrieval

### 5. Testing

1. Connection and authentication
2. CRUD operations
3. SQL script execution
4. Role-based access
5. All application features with Oracle backend

### 6. Update Documentation

1. Update environment variable documentation
2. Document Oracle-specific configuration
3. Update deployment instructions

## Oracle-Specific Considerations

- Case sensitivity: Oracle stores identifiers in UPPERCASE by default
- Transaction management: Explicit commits required
- Bind variable limits: Oracle has a limit on the number of bind variables
- Function differences: Different date/string manipulation functions
- PL/SQL vs PostgreSQL procedural language differences

## Files to Update

See the *.oracle.comments files for specific changes required for each file.
