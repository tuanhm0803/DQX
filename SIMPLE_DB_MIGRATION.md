# Simple Database Migration Guide

## Current Setup (PostgreSQL)
The application uses PostgreSQL with psycopg2.

## Switching to Oracle (Future)

### 1. Install Oracle Driver
```bash
pip install oracledb
```

### 2. Update Environment Variables
Copy `.env.example` to `.env` and update:

```env
# Change database type
DB_TYPE=oracle

# Update connection settings
DB_HOST=your-oracle-host
DB_PORT=1521
DB_SERVICE=XEPDB1
DB_USER=your-oracle-user
DB_PASSWORD=your-oracle-password
```

### 3. Oracle Timezone Fix
The application has been updated to handle Oracle thin mode timezone limitations:
- Uses naive datetime objects (no timezone info) to avoid DPY3022 errors
- Replaces `NOW()` with `SYSDATE` for Oracle compatibility
- Automatic query conversion for Oracle-specific syntax

### 4. Restart Application
```bash
python -m uvicorn app.main:app --reload
```

## Key Changes for Oracle Compatibility
- All `datetime.now()` calls use `.replace(tzinfo=None)` for Oracle
- SQL queries automatically convert `NOW()` to `SYSDATE`
- Database manager handles Oracle thick/thin mode configuration
- Unified error handling for both database types

## Benefits
- Easy switching with one environment variable change
- No more timezone errors (DPY3022) in Oracle thin mode
- Consistent code patterns for both databases
- Automatic query syntax conversion
