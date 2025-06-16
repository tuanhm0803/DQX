import psycopg2
from psycopg2.extensions import connection as PgConnection # For type hinting
from psycopg2 import sql # For safe SQL construction
import json
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict, List, Optional
import re

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
    return value

def _process_result_row(row: tuple, column_names: List[str]) -> Dict[str, Any]:
    """Process a single row of SQL query results"""
    return {col_name: _format_value_for_json(row_val) for col_name, row_val in zip(column_names, row)}

class TableStructureValidationError(ValueError):
    """Exception raised when table structure validation fails."""
    pass

def get_table_names(db: PgConnection) -> List[str]:
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

def get_table_structure(table_name: str, db: PgConnection) -> Dict[str, List[tuple]]:
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

def get_table_data(table_name: str, skip: int, limit: int, db: PgConnection) -> Dict[str, Any]:
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
        query = sql.SQL("SELECT {fields} FROM {schema}.{table} LIMIT %s OFFSET %s;").format(
            fields=sql.SQL(',').join(map(sql.Identifier, column_names)),
            schema=sql.Identifier('dq'),
            table=sql.Identifier(table_name)
        )
        cursor.execute(query, (limit, skip))
        result = cursor.fetchall()
        
        data = [_process_result_row(row, column_names) for row in result]
        
        # Get total count for pagination
        count_query = sql.SQL("SELECT COUNT(*) FROM {schema}.{table};").format(
            schema=sql.Identifier('dq'),
            table=sql.Identifier(table_name)
        )
        cursor.execute(count_query)
        total_count = cursor.fetchone()[0]
        
        return {"data": data, "total": total_count, "skip": skip, "limit": limit}
    finally:
        if cursor:
            cursor.close()

def insert_table_data(table_name: str, data: Dict[str, Any], db: PgConnection) -> Dict[str, Any]:
    """Insert data into a specific table using the provided DB connection"""
    cursor = None
    try:
        cursor = db.cursor()
        
        columns = list(data.keys()) # Ensure columns is a list for consistent ordering
        values = [data[column] for column in columns]
        
        # Check if 'id' column exists for RETURNING clause
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = %s AND column_name = 'id' AND table_schema = 'dq';", (table_name,))
        id_column_exists = cursor.fetchone()

        returning_sql = sql.SQL(" RETURNING id") if id_column_exists else sql.SQL("")

        query = sql.SQL("INSERT INTO {schema}.{table} ({cols}) VALUES ({vals}){returning}").format(
            schema=sql.Identifier('dq'),
            table=sql.Identifier(table_name),
            cols=sql.SQL(',').join(map(sql.Identifier, columns)),
            vals=sql.SQL(',').join(sql.Placeholder() * len(values)),
            returning=returning_sql
        )
        
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

def update_table_data(table_name: str, record_id: Any, data: Dict[str, Any], id_column: str, db: PgConnection) -> Dict[str, Any]:
    """Update data in a specific table by ID using the provided DB connection"""
    cursor = None
    try:
        cursor = db.cursor()
        
        set_clause_parts = []
        values = []
        for column, value in data.items():
            set_clause_parts.append(sql.SQL("{} = %s").format(sql.Identifier(column)))
            values.append(value)
        values.append(record_id) # Add record_id for the WHERE clause
        
        query = sql.SQL("UPDATE {schema}.{table} SET {set_parts} WHERE {id_col} = %s;").format(
            schema=sql.Identifier('dq'),
            table=sql.Identifier(table_name),
            set_parts=sql.SQL(', ').join(set_clause_parts),
            id_col=sql.Identifier(id_column)
        )
        
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

def delete_table_data(table_name: str, record_id: Any, id_column: str, db: PgConnection) -> Dict[str, Any]:
    """Delete data from a specific table by ID using the provided DB connection"""
    cursor = None
    try:
        cursor = db.cursor()
        query = sql.SQL("DELETE FROM {schema}.{table} WHERE {id_col} = %s;").format(
            schema=sql.Identifier('dq'),
            table=sql.Identifier(table_name),
            id_col=sql.Identifier(id_column)
        )
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

def execute_query(query_string: str, db: PgConnection) -> Dict[str, Any]:
    """Execute a custom SQL query (assumed SELECT) using the provided DB connection"""
    cursor = None
    if not query_string.strip().lower().startswith("select"):
        raise ValueError("Only SELECT queries are allowed for execute_query.")
    try:
        cursor = db.cursor()
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
def get_sql_scripts(db: PgConnection) -> List[Dict[str, Any]]:
    cursor = None
    try:
        cursor = db.cursor()
        cursor.execute("SELECT id, name, description, content, created_at, updated_at FROM dq.dq_sql_scripts ORDER BY created_at DESC;")
        scripts_tuples = cursor.fetchall()
        if not scripts_tuples:
            return []
        
        if cursor.description is None:
            raise ValueError("Failed to get column descriptions after fetching scripts.")
            
        column_names = [desc[0] for desc in cursor.description]
        return [_process_result_row(script_tuple, column_names) for script_tuple in scripts_tuples]
    except psycopg2.Error as db_err: # Catch database specific errors
        # Log db_err details server-side
        # Re-raise to be handled by the route, or wrap in a custom app exception
        raise # Propagates the psycopg2.Error
    except ValueError as val_err: # Catch ValueErrors like the one we added
        # Log val_err details server-side
        raise # Propagates the ValueError
    except Exception as e:
        # Log e details server-side
        # Wrap unexpected errors in a standard exception type or re-raise carefully
        raise RuntimeError(f"An unexpected error occurred in get_sql_scripts: {str(e)}") from e
    finally:
        if cursor:
            cursor.close()

def get_sql_script(db: PgConnection, script_id: int) -> Optional[Dict[str, Any]]:
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
    except psycopg2.Error as db_err:
        raise
    except ValueError as val_err:
        raise
    except Exception as e:
        raise RuntimeError(f"An unexpected error occurred in get_sql_script for ID {script_id}: {str(e)}") from e
    finally:
        if cursor:
            cursor.close()

def create_sql_script(db: PgConnection, script_data: Dict[str, Any]) -> Dict[str, Any]:
    cursor = None
    try:
        cursor = db.cursor()
        query = """
            INSERT INTO dq.dq_sql_scripts (name, description, content, created_at, updated_at)
            VALUES (%s, %s, %s, NOW(), NOW())
            RETURNING id, name, description, content, created_at, updated_at;
        """
        cursor.execute(query, (script_data['name'], script_data.get('description'), script_data['content']))
        new_script_tuple = cursor.fetchone()

        if not new_script_tuple:
            if db and not getattr(db, 'closed', True): db.rollback() # Rollback as the insert didn't return.
            raise ValueError("Insert operation did not return the new script. No script was created.")

        # If we got here, RETURNING worked, so commit.
        db.commit()

        if cursor.description is None:
            # This is highly unlikely if new_script_tuple is not None, but as a safeguard:
            raise ValueError("cursor.description is None after fetching a new script. Cannot determine column names.")

        column_names = [desc[0] for desc in cursor.description]
        return _process_result_row(new_script_tuple, column_names)

    except KeyError as ke:
        if db and not getattr(db, 'closed', True): db.rollback()
        raise ValueError(f"Missing required script data: {str(ke)}") from ke
    except psycopg2.Error: # Let psycopg2 errors propagate to be handled by the route
        if db and not getattr(db, 'closed', True): db.rollback()
        raise
    except ValueError: # If a ValueError is raised within try (like the ones above), rollback and re-raise
        if db and not getattr(db, 'closed', True): db.rollback() # Ensure rollback if not already done
        raise
    except Exception as e: # Catch any other unexpected error
        if db and not getattr(db, 'closed', True): db.rollback()
        raise RuntimeError(f"An unexpected issue occurred in CRUD operation for create_sql_script: {str(e)}") from e
    finally:
        if cursor:
            cursor.close()

def update_sql_script(db: PgConnection, script_id: int, script_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    cursor = None
    try:
        cursor = db.cursor()
        # Using .get for name and content as well, in case model_dump(exclude_unset=True) was used by caller
        # However, for a full update, these should ideally be present.
        # The route currently passes script.model_dump() without exclude_unset=True for PUT.
        name = script_data['name']
        description = script_data.get('description')
        content = script_data['content']

        query = """
            UPDATE dq.dq_sql_scripts
            SET name = %s, description = %s, content = %s, updated_at = NOW()
            WHERE id = %s
            RETURNING id, name, description, content, created_at, updated_at;
        """
        cursor.execute(query, (name, description, content, script_id))
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

def delete_sql_script(db: PgConnection, script_id: int) -> Dict[str, Any]:
    cursor = None
    try:
        cursor = db.cursor()
        cursor.execute("DELETE FROM dq.dq_sql_scripts WHERE id = %s;", (script_id,))
        deleted_rows = cursor.rowcount
        db.commit()
        if deleted_rows == 0:
            return {"success": False, "message": "Script not found or already deleted.", "deleted_rows": 0}
        return {"success": True, "deleted_rows": deleted_rows}
    except Exception:
        if db: db.rollback()
        raise
    finally:
        if cursor: cursor.close()

def execute_sql_script(db: PgConnection, script_content: str) -> Dict[str, Any]:
    """
    Executes the provided SQL script content.
    This function needs to be carefully designed to prevent harmful operations.
    """
    # Placeholder for any validation logic (e.g., TableStructureValidationError)
    # if "CREATE TABLE" in script_content.upper() and "STG." in script_content.upper():
    #     raise TableStructureValidationError("Creation of tables in STG schema with specific structure is required.")

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