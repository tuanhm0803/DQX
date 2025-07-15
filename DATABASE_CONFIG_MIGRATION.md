# Database Configuration Migration Guide

## Overview
The database configuration has been simplified to use individual parameters instead of URL strings, making it easier to switch between PostgreSQL and Oracle databases in the future.

## Changes Made

### 1. Role Permissions Simplification
- **Consolidated Functions**: Combined multiple permission functions into `can_admin_creator_access()` which replaces:
  - `can_create_table`
  - `can_insert_data`
  - `can_access_source_management`
  - `can_delete_scripts`
  - `can_delete_schedules`
  - `can_view_logs`

- **Updated Routes**: All routes now use the simplified permission function
- **Maintained Functionality**: Admin and creator roles still have the same access, inputters are still restricted

### 2. Environment Configuration
- **New Format**: Individual database parameters instead of URLs
- **Database Type Support**: Easy switching between PostgreSQL and Oracle
- **Backward Compatibility**: Still supports legacy URL format as fallback

## New .env Configuration Format

### Primary Database
```bash
# Database Type: postgresql or oracle
DB_TYPE=postgresql

# Database Connection Parameters
DB_HOST=localhost
DB_PORT=5432
DB_NAME=dqx
DB_USER=postgres
DB_PASSWORD=password
```

### Target Database (where tables are created)
```bash
TARGET_DB_NAME=Working Database
TARGET_DB_HOST=localhost
TARGET_DB_PORT=5432
TARGET_DB_NAME_DB=dqx
TARGET_DB_USER=postgres
TARGET_DB_PASSWORD=password
TARGET_DB_DESC=Primary working database where tables are created
```

### Source Databases (data sources)
```bash
# Production Source
DB_SOURCE_PROD_NAME=Production Database
DB_SOURCE_PROD_HOST=prod-server
DB_SOURCE_PROD_PORT=5432
DB_SOURCE_PROD_NAME_DB=prod_db
DB_SOURCE_PROD_USER=prod_user
DB_SOURCE_PROD_PASSWORD=prod_password
DB_SOURCE_PROD_DESC=Production database (source data)

# Staging Source
DB_SOURCE_STAGING_NAME=Staging Environment
DB_SOURCE_STAGING_HOST=staging-server
DB_SOURCE_STAGING_PORT=5432
DB_SOURCE_STAGING_NAME_DB=staging_db
DB_SOURCE_STAGING_USER=staging_user
DB_SOURCE_STAGING_PASSWORD=staging_password
DB_SOURCE_STAGING_DESC=Staging database (source data)
```

## Oracle Database Support

To switch to Oracle, simply change:
```bash
DB_TYPE=oracle
DB_HOST=oracle-server
DB_PORT=1521
DB_NAME=ORCL
DB_USER=dqx_user
DB_PASSWORD=dqx_password
```

## Migration Steps

1. **Update .env file**: Use the new individual parameter format
2. **Backward Compatibility**: Legacy `DATABASE_URL` format still works as fallback
3. **Test Connections**: Verify all database connections work with new format
4. **Code Changes**: No additional code changes needed - all handled automatically

## Benefits

1. **Easier Configuration**: Individual parameters are clearer than URL strings
2. **Database Flexibility**: Easy switching between PostgreSQL and Oracle
3. **Better Maintenance**: Clearer parameter separation
4. **Future Ready**: Prepared for Oracle integration
5. **Reduced Complexity**: Simplified permission system

## Files Modified

- `app/role_permissions.py` - Consolidated permission functions
- `app/database.py` - Added support for individual parameters and database types
- `app/multi_db_manager.py` - Refactored to support new configuration format
- `app/routes/*.py` - Updated to use new permission function
- `.env.example` - Updated with new format

## Testing

After updating your `.env` file with the new format, test:
1. Application startup
2. User authentication and permissions
3. Database connections (primary, target, source)
4. All existing functionality

The application should work exactly the same with improved configuration management.
