import psycopg2
import json
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict, List, Optional
import re
import os

# Get database type to handle Oracle-specific issues
DB_TYPE = os.getenv("DB_TYPE", "postgresql")

# --- Helper functions for database-agnostic operations ---

def _get_current_timestamp():
    """Get current timestamp in a database-agnostic way without timezone info"""
    # Return naive datetime to avoid Oracle thin mode timezone issues
    return datetime.now().replace(tzinfo=None)

def _convert_query_for_database(query: str) -> str:
    """Convert query syntax for the current database type"""
    if DB_TYPE == "oracle":
        # Replace NOW() with SYSDATE to avoid timezone issues in Oracle thin mode
        query = query.replace("NOW()", "SYSDATE")
        
        # Convert LIMIT/OFFSET for Oracle
        import re
        limit_pattern = r'\s+LIMIT\s+(\d+)(?:\s+OFFSET\s+(\d+))?\s*;?\s*$'
        match = re.search(limit_pattern, query, re.IGNORECASE)
        if match:
            limit = int(match.group(1))
            offset = int(match.group(2)) if match.group(2) else 0
            if offset > 0:
                replacement = f' OFFSET {offset} ROWS FETCH FIRST {limit} ROWS ONLY'
            else:
                replacement = f' FETCH FIRST {limit} ROWS ONLY'
            query = re.sub(limit_pattern, replacement, query, flags=re.IGNORECASE)
    
    return query

# --- Helper functions for safe SQL construction (Oracle-compatible) ---

def _quote_identifier(name: str) -> str:
    """
    Safely quote a SQL identifier (table name, column name, schema name).
    This replaces psycopg2's sql.Identifier functionality.
    Oracle-compatible: uses double quotes for identifiers.
    """
    # Remove any existing quotes and escape internal quotes
    clean_name = name.replace('"', '""')
    return f'"{clean_name}"'

def _build_placeholder_list(count: int) -> str:
    """
    Build a list of parameter placeholders.
    This replaces psycopg2's sql.Placeholder functionality.
    Oracle-compatible: uses :1, :2, etc. but for PostgreSQL we use %s
    """
    return ', '.join(['%s'] * count)

def _build_column_list(columns: List[str]) -> str:
    """
    Build a comma-separated list of quoted column identifiers.
    """
    return ', '.join(_quote_identifier(col) for col in columns)

# Import user CRUD operations
from app.user_crud import (
    create_user,
    get_user_by_id,
    get_user_by_username,
    get_user_by_email,
    update_user,
    deactivate_user
)

# --- Helper for stg table management ---

def _get_stg_table_name_str(script_id: int) -> str:
    """Generates the string name for a script's staging table."""
    return f"dq_script_{script_id}"

# --- SQL Script Validation ---

REQUIRED_COLUMNS = {"rule_id", "source_id", "source_uid", "data_value", "txn_date"}

def _validate_sql_script_columns(sql_content: str):
    """
    Validates that the SQL script is a SELECT statement and contains exactly the required columns.
    Raises ValueError if validation fails.
    """
    # Normalize the SQL content
    sql_lower = sql_content.strip().lower()
    if sql_lower.endswith(';'):
        sql_lower = sql_lower[:-1].strip()

    if not sql_lower.startswith('select'):
        raise ValueError("Invalid script. Only SELECT statements are allowed.")

    # Find the end of the column list. This could be the start of a 'FROM' clause
    # or the end of the query if no 'FROM' clause exists.
    from_match = re.search(r'\s+from\s+', sql_lower, re.IGNORECASE)
    
    if from_match:
        # If 'FROM' is found, columns are between 'SELECT' and 'FROM'
        columns_str = sql_lower[len('select'):from_match.start()].strip()
    else:
        # If no 'FROM', columns are everything after 'SELECT'
        columns_str = sql_lower[len('select'):].strip()

    if not columns_str:
        raise ValueError("Invalid SELECT statement. Could not find column list.")

    raw_column_parts = columns_str.split(',')
    extracted_columns = set()

    for part_str in raw_column_parts:
        part_str = part_str.strip()
        
        # Regex to capture the alias if 'AS alias_name' pattern is used.
        # It captures the expression before 'AS' and the alias_name itself.
        # Alias name is restricted to simple identifiers for this validation.
        alias_match = re.match(r'(.*)\s+as\s+([a-z0-9_]+)$', part_str, re.IGNORECASE)
        
        if alias_match:
            # If an alias is found, use the alias name
            column_name = alias_match.group(2).strip()
        else:
            # No 'AS alias_name' pattern found. 
            # This means it's either a direct column name (e.g., rule_id) 
            # or an expression without an alias (e.g., CURRENT_DATE).
            # If it's an expression like CURRENT_DATE, it must be one of the REQUIRED_COLUMNS names itself,
            # or it should have been aliased.
            # For table.column or schema.table.column, take the last part.
            if '.' in part_str:
                column_name = part_str.split('.')[-1].strip()
            else:
                column_name = part_str.strip()
        
        # Remove any surrounding quotes from the final determined column name
        # (though the alias regex `([a-z0-9_]+)` shouldn't capture quotes for the alias itself)
        column_name = column_name.strip('\'\"`') # Corrected line
        extracted_columns.add(column_name.lower()) # Add as lowercase

    if extracted_columns != REQUIRED_COLUMNS:
        missing = REQUIRED_COLUMNS - extracted_columns
        extra = extracted_columns - REQUIRED_COLUMNS
        error_parts = []
        if missing:
            error_parts.append(f"Missing required columns: {sorted(list(missing))}")
        if extra:
            error_parts.append(f"Disallowed columns found: {sorted(list(extra))}")
        
        raise ValueError(f"SQL script does not match required format. {'. '.join(error_parts)}")

# Custom JSON encoder to handle special data types
class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, bytes):
            return obj.hex() # More standard way to represent bytes
        return super().default(obj)

def _format_value_for_json(value: Any) -> Any:
    """Format a database value for JSON serialization"""
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    elif isinstance(value, Decimal):
        return float(value)
    elif isinstance(value, (bytes, bytearray)):
        try:
            return value.decode('utf-8') # Try to decode if it's text
        except UnicodeDecodeError:
            return value.hex() # Fallback to hex if not valid UTF-8
    # For other types, attempt to return as is, relying on JSONEncoder for complex ones
    try:
        return str(value)
    except (TypeError, ValueError):
        return str(value)

def _process_result_row(row: tuple, column_names: List[str]) -> Dict[str, Any]:
    """Converts a database row tuple to a dictionary with column names, formatting values."""
    if row is None:
        return None
    return dict(zip(column_names, [_format_value_for_json(v) for v in row]))

def get_script_count(db) -> int:
    """Gets the total number of SQL scripts."""
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM dq.dq_sql_scripts")
            count = cursor.fetchone()[0]
            return count
    except Exception as e:
        print(f"Error getting script count: {str(e)}")
        return 0  # Return 0 if there's an error (e.g., table doesn't exist)

def get_bad_detail_count(db) -> int:
    """Gets the total number of records in the bad_detail table."""
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM dq.bad_detail")
            count = cursor.fetchone()[0]
            return count
    except Exception as e:
        print(f"Error getting bad_detail count: {str(e)}")
        return 0  # Return 0 if there's an error (e.g., table doesn't exist)

def get_stats(db):
    script_count = get_script_count(db)
    bad_detail_count = get_bad_detail_count(db)
    return {"script_count": script_count, "bad_detail_count": bad_detail_count}

# --- Table Operations ---

def get_schemas(db) -> List[str]:
    """Get all schemas in the database"""
    cursor = None
    try:
        cursor = db.cursor()
        cursor.execute("SELECT schema_name FROM information_schema.schemata;")
        schemas = [row[0] for row in cursor.fetchall()]
        return schemas
    finally:
        if cursor:
            cursor.close()

# --- DQ Table Operations ---

def get_dq_table_names(db) -> List[str]:
    """Get all tables in the 'DQ' schema using the provided DB connection"""
    cursor = None
    try:
        cursor = db.cursor()
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'dq';")
        tables = [row[0] for row in cursor.fetchall()]
        return tables
    finally:
        if cursor:
            cursor.close()

def get_dq_table_structure(table_name: str, db) -> Dict[str, List[tuple]]:
    """Get the structure of a specific table using the provided DB connection"""
    cursor = None
    try:
        cursor = db.cursor()
        # Use normal string, not f-string, when using %s placeholders
        cursor.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = %s AND table_schema = 'dq';", (table_name,))
        columns = cursor.fetchall()
        return {"columns": columns}
    finally:
        if cursor:
            cursor.close()

def get_dq_table_data(table_name: str, skip: int, limit: int, db) -> Dict[str, Any]:
    """Get data from a specific table with pagination using the provided DB connection"""
    cursor = None
    try:
        cursor = db.cursor()
        
        # Get column names first
        # Use normal string, not f-string, when using %s placeholders
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = %s AND table_schema = 'dq' ORDER BY ordinal_position;", (table_name,))
        column_names_result = cursor.fetchall()
        if not column_names_result:
            raise ValueError(f"Table '{table_name}' not found or has no columns in schema 'dq'.")
        column_names = [row[0] for row in column_names_result]

        # Fetch data
        fields = _build_column_list(column_names)
        query = f"SELECT {fields} FROM {_quote_identifier('dq')}.{_quote_identifier(table_name)} LIMIT %s OFFSET %s;"
        cursor.execute(query, (limit, skip))
        result = cursor.fetchall()
        
        data = [_process_result_row(row, column_names) for row in result]
        
        # Get total count for pagination
        count_query = f"SELECT COUNT(*) FROM {_quote_identifier('dq')}.{_quote_identifier(table_name)};"
        cursor.execute(count_query)
        total_count = cursor.fetchone()[0]
        
        return {"data": data, "total": total_count, "skip": skip, "limit": limit}
    finally:
        if cursor:
            cursor.close()

def insert_table_data(table_name: str, data: Dict[str, Any], db) -> Dict[str, Any]:
    """Insert data into a specific table using the provided DB connection"""
    cursor = None
    try:
        cursor = db.cursor()
        
        columns = list(data.keys()) # Ensure columns is a list for consistent ordering
        values = [data[column] for column in columns]
        
        # Check if 'id' column exists for RETURNING clause
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = %s AND column_name = 'id' AND table_schema = 'dq';", (table_name,))
        id_column_exists = cursor.fetchone()

        returning_sql = " RETURNING id" if id_column_exists else ""
        cols = _build_column_list(columns)
        vals = _build_placeholder_list(len(values))

        query = f"INSERT INTO {_quote_identifier('dq')}.{_quote_identifier(table_name)} ({cols}) VALUES ({vals}){returning_sql};"
        
        cursor.execute(query, values)
        inserted_id = None
        if id_column_exists and cursor.rowcount > 0 and cursor.description: # Check description before fetchone
            inserted_id = cursor.fetchone()[0]
        
        db.commit()
        return {"success": True, "id": inserted_id, "inserted_rows": cursor.rowcount}
    except Exception:
        if db:
            db.rollback()
        raise # Re-raise the caught exception
    finally:
        if cursor:
            cursor.close()

def update_table_data(table_name: str, record_id: Any, data: Dict[str, Any], id_column: str, db) -> Dict[str, Any]:
    """Update data in a specific table by ID using the provided DB connection"""
    cursor = None
    try:
        cursor = db.cursor()
        
        set_clause_parts = []
        values = []
        for column, value in data.items():
            set_clause_parts.append(f"{_quote_identifier(column)} = %s")
            values.append(value)
        values.append(record_id) # Add record_id for the WHERE clause
        
        set_parts = ', '.join(set_clause_parts)
        query = f"UPDATE {_quote_identifier('dq')}.{_quote_identifier(table_name)} SET {set_parts} WHERE {_quote_identifier(id_column)} = %s;"
        
        cursor.execute(query, values)
        updated_rows = cursor.rowcount
        db.commit()
        return {"success": True, "updated_rows": updated_rows}
    except Exception:
        if db:
            db.rollback()
        raise
    finally:
        if cursor:
            cursor.close()

def delete_table_data(table_name: str, record_id: Any, id_column: str, db) -> Dict[str, Any]:
    """Delete data from a specific table by ID using the provided DB connection"""
    cursor = None
    try:
        cursor = db.cursor()
        query = f"DELETE FROM {_quote_identifier('dq')}.{_quote_identifier(table_name)} WHERE {_quote_identifier(id_column)} = %s;"
        cursor.execute(query, (record_id,))
        deleted_rows = cursor.rowcount
        db.commit()
        return {"success": True, "deleted_rows": deleted_rows}
    except Exception:
        if db:
            db.rollback()
        raise
    finally:
        if cursor:
            cursor.close()

def execute_query(query_string: str, db, params=None) -> Dict[str, Any]:
    """Execute a custom SQL query (assumed SELECT) using the provided DB connection with optional parameters"""
    cursor = None
    if not query_string.strip().lower().startswith("select"):
        raise ValueError("Only SELECT queries are allowed for execute_query.")
    try:
        cursor = db.cursor()
        if params:
            cursor.execute(query_string, params)
        else:
            cursor.execute(query_string)
        
        if cursor.description: 
            column_names = [desc[0] for desc in cursor.description]
            result = cursor.fetchall()
            data = [_process_result_row(row, column_names) for row in result]
            return {"data": data, "count": len(data), "columns": column_names}
        else: 
            return {"message": "Query executed successfully.", "rowcount": cursor.rowcount}

    except Exception:
        # SELECT queries don't typically need rollback unless part of a larger transaction
        # that might have been started implicitly by FastAPI/Starlette.
        # However, get_db now yields the connection, so rollback might be handled by the caller or context.
        # For safety, if an error occurs during SELECT, a rollback won't hurt.
        if db:
             db.rollback() # Added rollback for consistency, though SELECTs are usually read-only.
        raise
    finally:
        if cursor:
            cursor.close()

# --- SQL Script Management Functions ---
def get_sql_scripts(db) -> List[Dict[str, Any]]:
    """Get all saved SQL scripts from the database"""
    cursor = None
    try:
        cursor = db.cursor()
        # Added ORDER BY for consistent ordering and debugging
        query = f"SELECT id, name, description, content, created_at, updated_at FROM {_quote_identifier('dq')}.{_quote_identifier('dq_sql_scripts')} ORDER BY id ASC;"
        cursor.execute(query)
        
        fetched_rows = cursor.fetchall()
        # Added for debugging to see what the database returns
        print("Fetched rows from dq_sql_scripts:", fetched_rows) 

        scripts = []
        if not cursor.description:
            return [] # Return empty list if no columns/data

        column_names = [desc[0] for desc in cursor.description]
        
        if 'id' not in column_names:
            raise ValueError("The 'id' column is missing from the dq_sql_scripts table.")

        id_index = column_names.index('id')

        for row in fetched_rows:
            if row[id_index] is None:
                print(f"Skipping script with NULL ID: {row}")
                continue
            
            script_dict = {col: val for col, val in zip(column_names, row)}
            
            # Final check before appending to be extra safe
            if 'id' not in script_dict or script_dict['id'] is None:
                print(f"Skipping script with missing or NULL ID after processing: {script_dict}")
                continue

            scripts.append(script_dict)

        return scripts

    except psycopg2.Error as db_err:
        raise ValueError(f"Database query failed: {str(db_err)}") from db_err
    except ValueError as val_err:
        raise val_err
    except Exception as e:
        raise RuntimeError(f"An unexpected error occurred in get_sql_scripts: {str(e)}") from e
    finally:
        if cursor:
            cursor.close()

def get_sql_script(db, script_id: int) -> Optional[Dict[str, Any]]:
    cursor = None
    try:
        cursor = db.cursor()
        cursor.execute("SELECT id, name, description, content, created_at, updated_at FROM dq.dq_sql_scripts WHERE id = %s;", (script_id,))
        script_tuple = cursor.fetchone()
        if not script_tuple:
            return None

        if cursor.description is None:
            raise ValueError(f"Failed to get column descriptions for script ID {script_id}.")

        column_names = [desc[0] for desc in cursor.description]
        return _process_result_row(script_tuple, column_names)
    except psycopg2.Error:
        raise
    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError(f"An unexpected error occurred in get_sql_script for ID {script_id}: {str(e)}") from e
    finally:
        if cursor:
            cursor.close()

def create_sql_script(db, script_data: Dict[str, Any]) -> Dict[str, Any]:
    """Creates a new SQL script and its corresponding staging table."""
    cursor = None
    try:
        # Validate the script content before proceeding
        _validate_sql_script_columns(script_data['content'])

        cursor = db.cursor()

        # --- Check for existing script with the same name ---
        script_name = script_data.get('name')
        if not script_name:
            raise ValueError("Script name cannot be empty.")
        
        cursor.execute("SELECT id FROM dq.dq_sql_scripts WHERE name = %s;", (script_name,))
        if cursor.fetchone():
            raise ValueError(f"A script with the name '{script_name}' already exists.")
        # --- End of new logic ---

        # Start transaction
        current_time = _get_current_timestamp()
        query = """
            INSERT INTO dq.dq_sql_scripts (name, description, content, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, name, description, content, created_at, updated_at;
        """
        cursor.execute(query, (script_data['name'], script_data.get('description'), script_data['content'], current_time, current_time))
        new_script_tuple = cursor.fetchone()

        if not new_script_tuple:
            if db and not getattr(db, 'closed', True): db.rollback()
            raise ValueError("Insert operation did not return the new script. No script was created.")

        if cursor.description is None:
            if db and not getattr(db, 'closed', True): db.rollback()
            raise ValueError("cursor.description is None after fetching a new script. Cannot determine column names.")

        column_names = [desc[0] for desc in cursor.description]
        
        # Directly find the ID from the returned tuple to be more robust
        try:
            id_index = column_names.index('id')
        except ValueError:
            db.rollback()
            raise ValueError("Fatal: 'id' column not found in RETURNING clause result.") from None

        new_id = new_script_tuple[id_index]

        if not new_id:
            db.rollback()
            # This is the most likely cause of the original error.
            raise ValueError("Failed to retrieve ID for the newly created script (database returned NULL).")

        # Now that we have a valid ID, we can process the rest of the data
        new_script_dict = _process_result_row(new_script_tuple, column_names)

        # --- Create the corresponding staging table ---
        stg_table_name_str = _get_stg_table_name_str(new_id)
        
        # Drop if it somehow exists to ensure a clean slate
        drop_table_query = f"DROP TABLE IF EXISTS {_quote_identifier('stg')}.{_quote_identifier(stg_table_name_str)};"
        cursor.execute(drop_table_query)

        # Sanitize script content for use in DDL
        clean_script_content = script_data['content'].strip()
        if clean_script_content.endswith(';'):
            clean_script_content = clean_script_content[:-1]

        # Create the table based on the script's output structure
        create_table_query = f"CREATE TABLE {_quote_identifier('stg')}.{_quote_identifier(stg_table_name_str)} AS ({clean_script_content}) WITH NO DATA;"
        cursor.execute(create_table_query)
        # --- End of new logic ---

        db.commit() # Commit both the insert and the create table

        return new_script_dict

    except KeyError as ke:
        if db and not getattr(db, 'closed', True): db.rollback()
        raise ValueError(f"Missing required script data: {str(ke)}") from ke
    except psycopg2.Error:
        if db and not getattr(db, 'closed', True): db.rollback()
        raise
    except ValueError:
        if db and not getattr(db, 'closed', True): db.rollback()
        raise
    except Exception as e:
        if db and not getattr(db, 'closed', True): db.rollback()
        raise RuntimeError(f"An unexpected issue occurred in CRUD operation for create_sql_script: {str(e)}") from e
    finally:
        if cursor:
            cursor.close()


def update_sql_script(db, script_id: int, script_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Updates an existing SQL script after validating its new content."""
    cursor = None
    try:
        # Validate the new script content before proceeding
        _validate_sql_script_columns(script_data['content'])

        cursor = db.cursor()
        # Using .get for name and content as well, in case model_dump(exclude_unset=True) was used by caller
        # However, for a full update, these should ideally be present.
        # The route currently passes script.model_dump() without exclude_unset=True for PUT.
        name = script_data['name']

        # --- Check if another script with the same name exists ---
        cursor.execute("SELECT id FROM dq.dq_sql_scripts WHERE name = %s AND id != %s;", (name, script_id))
        if cursor.fetchone():
            raise ValueError(f"Another script with the name '{name}' already exists.")
        # --- End of new logic ---
        
        description = script_data.get('description')
        content = script_data['content']
        current_time = _get_current_timestamp()

        query = """
            UPDATE dq.dq_sql_scripts
            SET name = %s, description = %s, content = %s, updated_at = %s
            WHERE id = %s
            RETURNING id, name, description, content, created_at, updated_at;
        """
        cursor.execute(query, (name, description, content, current_time, script_id))
        updated_script_tuple = cursor.fetchone()

        if not updated_script_tuple:
            if db and not getattr(db, 'closed', True): db.rollback()
            # Return None as per original signature, route will handle 404 if this means "not found"
            # Or, could raise ValueError("Update operation did not return the script or script not found.")
            return None 

        db.commit()

        if cursor.description is None:
             raise ValueError("cursor.description is None after fetching updated script. Cannot determine column names.")
        
        column_names = [desc[0] for desc in cursor.description]
        return _process_result_row(updated_script_tuple, column_names)
    
    except KeyError as ke:
        if db and not getattr(db, 'closed', True): db.rollback()
        raise ValueError(f"Missing required script data for update: {str(ke)}") from ke
    except psycopg2.Error:
        if db and not getattr(db, 'closed', True): db.rollback()
        raise
    except ValueError: # If a ValueError is raised within try
        if db and not getattr(db, 'closed', True): db.rollback()
        raise
    except Exception as e:
        if db and not getattr(db, 'closed', True): db.rollback()
        raise RuntimeError(f"An unexpected issue occurred in CRUD operation for update_sql_script: {str(e)}") from e
    finally:
        if cursor:
            cursor.close()

def delete_sql_script(db, script_id: int) -> Dict[str, Any]:
    cursor = None
    try:
        cursor = db.cursor()

        # --- Drop the corresponding staging table ---
        stg_table_name_str = _get_stg_table_name_str(script_id)
        drop_table_query = f"DROP TABLE IF EXISTS {_quote_identifier('stg')}.{_quote_identifier(stg_table_name_str)};"
        cursor.execute(drop_table_query)
        # --- End of new logic ---

        cursor.execute("DELETE FROM dq.dq_sql_scripts WHERE id = %s;", (script_id,))
        deleted_rows = cursor.rowcount
        
        db.commit() # Commit both the drop and the delete
        
        if deleted_rows == 0:
            return {"success": False, "message": "Script not found or already deleted.", "deleted_rows": 0}
        return {"success": True, "deleted_rows": deleted_rows}
    except Exception:
        if db: db.rollback()
        raise
    finally:
        if cursor: cursor.close()


def execute_sql_script(db, script_content: str) -> Dict[str, Any]:
    """
    Executes the provided SQL script content after validating its structure.
    This function needs to be carefully designed to prevent harmful operations.
    """
    # Hotfix to swap arguments if they are passed in the wrong order
    if isinstance(db, str) and hasattr(script_content, 'cursor'):
        db, script_content = script_content, db

    # First, validate the script structure and columns.
    _validate_sql_script_columns(script_content)

    cursor = None
    try:
        cursor = db.cursor()
        # psycopg2 executes the entire string, which can include multiple statements
        # separated by semicolons if the server is configured to allow it,
        # or if it's a single complex statement.
        # However, cursor.description and fetchall() will typically relate to the *last*
        # command that produces results if multiple statements are executed.
        # For more complex multi-statement scripts, consider splitting or using a library.
        cursor.execute(script_content)
        
        results = []
        columns = []

        # Check if the last executed part of the script returned data
        if cursor.description: 
            columns = [desc[0] for desc in cursor.description]
            fetched_rows = cursor.fetchall()
            for row in fetched_rows:
                results.append(_process_result_row(row, columns))
        
        # Commit if the script likely contained DML (not just SELECT)
        # This is a heuristic. A more robust way is to parse the script or rely on explicit transaction control.
        script_lower_trimmed = script_content.strip().lower()
        if not script_lower_trimmed.startswith("select") and "returning" not in script_lower_trimmed :
             # If it's not a select, and not a DML with RETURNING (which commits implicitly sometimes or is handled by autocommit)
             # then explicitly commit. This is broad; ideally, the script itself or the calling context handles transactions.
             # For now, we commit if it's not clearly a read-only operation.
            if cursor.rowcount > 0 or any(kw in script_lower_trimmed for kw in ["insert", "update", "delete", "create", "alter", "drop", "truncate"]):
                 db.commit()
            
        return {
            "message": "Script executed successfully.", 
            "rowcount": cursor.rowcount, 
            "columns": columns, 
            "data": results      
        }

    except psycopg2.Error as db_err:
        if db: db.rollback()
        # Re-raise as a ValueError to be caught by the route handler, which will convert to HTTPException
        raise ValueError(f"Database error: {db_err.pgcode if db_err.pgcode else ''} - {db_err.pgerror if db_err.pgerror else str(db_err)}") from db_err
    except Exception as e:
        if db: db.rollback()
        raise ValueError(f"Execution failed: {str(e)}") from e
    finally:
        if cursor:
            cursor.close()

# --- New function for populating stg table ---
def populate_script_result_table(db, script_id: int) -> Dict[str, Any]:
    """
    Executes a SQL script and inserts the results into its dedicated staging table.
    The staging table is created if it doesn't exist, and truncated before insertion.
    """
    cursor = None
    try:
        # 1. Get the script content
        script_info = get_sql_script(db, script_id)
        if not script_info or 'content' not in script_info:
            raise ValueError(f"Script with ID {script_id} not found.")
        
        script_content = script_info['content']
        stg_table_name_str = _get_stg_table_name_str(script_id)
        
        # Sanitize script content for use in DDL/DML
        clean_script_content = script_content.strip()
        if clean_script_content.endswith(';'):
            clean_script_content = clean_script_content[:-1]

        cursor = db.cursor()

        # 2. Ensure the staging table exists, creating it if necessary
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = %s AND table_name = %s
            )
        """, ('stg', stg_table_name_str))
        table_exists = cursor.fetchone()[0]

        if not table_exists:
            # Create the table if it does not exist
            create_table_query = f"CREATE TABLE {_quote_identifier('stg')}.{_quote_identifier(stg_table_name_str)} AS ({clean_script_content}) WITH NO DATA;"
            cursor.execute(create_table_query)
        else:
            # If it exists, truncate it to clear old data
            truncate_query = f"TRUNCATE TABLE {_quote_identifier('stg')}.{_quote_identifier(stg_table_name_str)};"
            cursor.execute(truncate_query)

        # 3. Insert data from the script into the staging table
        insert_query = f"INSERT INTO {_quote_identifier('stg')}.{_quote_identifier(stg_table_name_str)} {clean_script_content};"
        cursor.execute(insert_query)
        inserted_rows = cursor.rowcount
        
        db.commit()
        
        return {"success": True, "inserted_rows": inserted_rows, "table": f"stg.{stg_table_name_str}"}

    except Exception:
        if db: db.rollback()
        raise
    finally:
        if cursor: cursor.close()

def publish_script_results(db, script_id: int) -> Dict[str, Any]:
    """
    Publishes results from a script's staging table to the central dq.bad_detail table.
    For each (rule_id, source_id) pair in the staging table, it deletes existing
    records from dq.bad_detail and then inserts the new ones.
    """
    cursor = None
    stg_table_name_str = _get_stg_table_name_str(script_id)
    
    try:
        cursor = db.cursor()

        # 1. Get distinct (rule_id, source_id) pairs from the staging table.
        get_keys_query = f"SELECT DISTINCT rule_id, source_id FROM {_quote_identifier('stg')}.{_quote_identifier(stg_table_name_str)};"
        cursor.execute(get_keys_query)
        keys_to_replace = cursor.fetchall()

        if not keys_to_replace:
            # If the staging table is empty, there's nothing to publish.
            return {"success": True, "message": "Staging table is empty. Nothing to publish.", "published_rows": 0}
        
        # 2. Delete existing records from dq.bad_detail that match these keys.
        # The argument for 'IN %s' needs to be a tuple of tuples.
        delete_query = f"DELETE FROM {_quote_identifier('dq')}.{_quote_identifier('bad_detail')} WHERE (rule_id, source_id) IN %s;"
        cursor.execute(delete_query, (tuple(keys_to_replace),))

        # 3. Insert the new records from the staging table.
        # The column names are known and validated to be correct when the script was saved.
        insert_query = f"""
            INSERT INTO {_quote_identifier('dq')}.{_quote_identifier('bad_detail')} (rule_id, source_id, source_uid, data_value, txn_date)
            SELECT rule_id, source_id, source_uid, data_value, txn_date
            FROM {_quote_identifier('stg')}.{_quote_identifier(stg_table_name_str)};
        """
        cursor.execute(insert_query)
        published_rows = cursor.rowcount

        db.commit()

        return {"success": True, "published_rows": published_rows, "keys_replaced_count": len(keys_to_replace)}

    except Exception:
        if db: db.rollback()
        raise
    finally:
        if cursor: cursor.close()

# --- Schedule Management Functions ---

def create_schedule(db, schedule: Dict[str, Any]) -> Dict[str, Any]:
    """Creates a new schedule."""
    cursor = None
    try:
        cursor = db.cursor()
        query = """
            INSERT INTO dq.dq_schedules (job_name, script_id, cron_schedule, is_active)
            VALUES (%s, %s, %s, %s)
            RETURNING id, job_name, script_id, cron_schedule, is_active, created_at, updated_at;
        """
        cursor.execute(query, (
            schedule['job_name'],
            schedule['script_id'],
            schedule['cron_schedule'],
            schedule.get('is_active', True)
        ))
        new_schedule_tuple = cursor.fetchone()
        db.commit()

        if not new_schedule_tuple:
            raise ValueError("Failed to create schedule.")

        column_names = [desc[0] for desc in cursor.description]
        return _process_result_row(new_schedule_tuple, column_names)
    finally:
        if cursor:
            cursor.close()

def get_schedules(db) -> List[Dict[str, Any]]:
    """Gets all schedules."""
    cursor = None
    try:
        cursor = db.cursor()
        query = "SELECT s.id, s.job_name, s.script_id, sc.name as script_name, s.cron_schedule, s.is_active, s.created_at, s.updated_at FROM dq.dq_schedules s JOIN dq.dq_sql_scripts sc ON s.script_id = sc.id ORDER BY s.id ASC;"
        cursor.execute(query)
        schedules_tuples = cursor.fetchall()

        if not schedules_tuples:
            return []

        column_names = [desc[0] for desc in cursor.description]
        return [_process_result_row(row, column_names) for row in schedules_tuples]
    finally:
        if cursor:
            cursor.close()

def get_schedule(db, schedule_id: int) -> Optional[Dict[str, Any]]:
    """Gets a single schedule by its ID."""
    cursor = None
    try:
        cursor = db.cursor()
        query = "SELECT id, job_name, script_id, cron_schedule, is_active, created_at, updated_at FROM dq.dq_schedules WHERE id = %s;"
        cursor.execute(query, (schedule_id,))
        schedule_tuple = cursor.fetchone()

        if not schedule_tuple:
            return None

        column_names = [desc[0] for desc in cursor.description]
        return _process_result_row(schedule_tuple, column_names)
    finally:
        if cursor:
            cursor.close()

def update_schedule(db, schedule_id: int, schedule_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Updates an existing schedule."""
    cursor = None
    try:
        cursor = db.cursor()

        # Construct the SET clause dynamically
        set_parts = []
        values = []
        for key, value in schedule_data.items():
            if value is not None:
                set_parts.append(f"{_quote_identifier(key)} = %s")
                values.append(value)

        if not set_parts:
            return get_schedule(db, schedule_id)

        values.append(schedule_id)
        set_clause = ', '.join(set_parts)

        query = f"UPDATE dq.dq_schedules SET {set_clause} WHERE id = %s RETURNING id, job_name, script_id, cron_schedule, is_active, created_at, updated_at;"

        cursor.execute(query, values)
        updated_schedule_tuple = cursor.fetchone()
        db.commit()

        if not updated_schedule_tuple:
            return None

        column_names = [desc[0] for desc in cursor.description]
        return _process_result_row(updated_schedule_tuple, column_names)
    finally:
        if cursor:
            cursor.close()

def delete_schedule(db, schedule_id: int) -> Dict[str, Any]:
    """Deletes a schedule."""
    cursor = None
    try:
        cursor = db.cursor()
        query = "DELETE FROM dq.dq_schedules WHERE id = %s;"
        cursor.execute(query, (schedule_id,))
        deleted_rows = cursor.rowcount
        db.commit()
        return {"success": deleted_rows > 0, "deleted_rows": deleted_rows}
    finally:
        if cursor:
            cursor.close()