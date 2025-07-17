# Oracle Identifier Quoting Fix

## Problem
In Oracle, object names (schemas, tables, columns) are automatically converted to uppercase unless they are quoted with double quotes. The previous `_quote_identifier` function always added quotes, which could cause "object not found" errors in Oracle when it expected uppercase names.

## Solution
Updated the `_quote_identifier` function in `app/crud.py` to be database-aware:

### For Oracle:
- Only quotes identifiers when necessary:
  - Contains special characters or spaces
  - Contains lowercase letters (needs case preservation)
  - Is a reserved word
- Otherwise, lets Oracle handle the uppercase conversion naturally

### For PostgreSQL and other databases:
- Always quotes to preserve exact case (existing behavior)

## Example Behavior

### PostgreSQL (DB_TYPE=postgresql):
```python
_quote_identifier("DQ")          # Returns: "DQ"
_quote_identifier("table_name")  # Returns: "table_name"
_quote_identifier("Column")      # Returns: "Column"
```

### Oracle (DB_TYPE=oracle):
```python
_quote_identifier("DQ")          # Returns: DQ (Oracle converts to uppercase)
_quote_identifier("table_name")  # Returns: "table_name" (contains lowercase)
_quote_identifier("user")        # Returns: "user" (reserved word)
_quote_identifier("MY_TABLE")    # Returns: MY_TABLE (uppercase, no special chars)
```

## Changes Made
1. Added `DB_TYPE` import from environment variables
2. Updated `_quote_identifier` function with database-specific logic
3. Added reserved word detection for Oracle
4. Maintained backward compatibility for PostgreSQL

## Testing
- Application starts successfully
- CRUD module imports without errors
- Existing PostgreSQL functionality preserved
- Oracle compatibility improved

## Files Modified
- `app/crud.py`: Updated `_quote_identifier` function and added database type detection
