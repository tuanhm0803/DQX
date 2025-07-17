"""
Main CRUD operations for the DQX application.
Handles database operations for SQL scripts, table management, and execution.
"""

import psycopg2
import json
import os
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict, List, Optional
import re

# Import user CRUD operations
from app.user_crud import (
    create_user,
    get_user_by_id,
    get_user_by_username,
    get_user_by_email,
    update_user,
    deactivate_user
)

# Get database type from environment
DB_TYPE = os.getenv("DB_TYPE", "postgresql").lower()


# ========================================================================================
# HELPER FUNCTIONS
# ========================================================================================

def _build_placeholder_list(count: int) -> str:
    """Build a list of parameter placeholders for the current database type."""
    if DB_TYPE == "oracle":
        # Oracle uses numbered placeholders like :1, :2, :3
        return ', '.join([f":{i+1}" for i in range(count)])
    else:
        # PostgreSQL and others use %s
        return ', '.join(['%s'] * count)


def _build_column_list(columns: List[str]) -> str:
    """Build a comma-separated list of column identifiers."""
    return ', '.join(columns)


def _get_stg_table_name_str(script_id: int) -> str:
    """Generate the string name for a script's staging table."""
    return f"dq_script_{script_id}"


def _format_value_for_json(value: Any) -> Any:
    """Format a database value for JSON serialization."""
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    elif isinstance(value, Decimal):
        return float(value)
    elif isinstance(value, (bytes, bytearray)):
        try:
            return value.decode('utf-8')
        except UnicodeDecodeError:
            return value.hex()
    try:
        return str(value)
    except (TypeError, ValueError):
        return str(value)


def _process_result_row(row: tuple, column_names: List[str]) -> Dict[str, Any]:
    """Convert a database row tuple to a dictionary with column names."""
    if row is None:
        return None
    return dict(zip(column_names, [_format_value_for_json(v) for v in row]))


class JSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for special data types."""
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, bytes):
            return obj.hex()
        return super().default(obj)


# ========================================================================================
# SQL SCRIPT VALIDATION
# ========================================================================================

REQUIRED_COLUMNS = {"rule_id", "source_id", "source_uid", "data_value", "txn_date"}


def _validate_sql_script_columns(sql_content: str):
    """Validate that the SQL script contains exactly the required columns."""
    sql_lower = sql_content.strip().lower()
    if sql_lower.endswith(';'):
        sql_lower = sql_lower[:-1].strip()

    if not sql_lower.startswith('select'):
        raise ValueError("Invalid script. Only SELECT statements are allowed.")

    # Find column list between SELECT and FROM
    from_match = re.search(r'\s+from\s+', sql_lower, re.IGNORECASE)
    
    if from_match:
        columns_str = sql_lower[len('select'):from_match.start()].strip()
    else:
        columns_str = sql_lower[len('select'):].strip()

    if not columns_str:
        raise ValueError("Invalid SELECT statement. Could not find column list.")

    raw_column_parts = columns_str.split(',')
    extracted_columns = set()

    for part_str in raw_column_parts:
        part_str = part_str.strip()
        
        # Handle aliases with 'AS'
        alias_match = re.match(r'(.*)\s+as\s+([a-z0-9_]+)$', part_str, re.IGNORECASE)
        
        if alias_match:
            column_name = alias_match.group(2).strip()
        else:
            # Handle table.column format
            if '.' in part_str:
                column_name = part_str.split('.')[-1].strip()
            else:
                column_name = part_str.strip()
        
        column_name = column_name.strip('\'\"`')
        extracted_columns.add(column_name.lower())

    if extracted_columns != REQUIRED_COLUMNS:
        missing = REQUIRED_COLUMNS - extracted_columns
        extra = extracted_columns - REQUIRED_COLUMNS
        error_parts = []
        if missing:
            error_parts.append(f"Missing required columns: {sorted(list(missing))}")
        if extra:
            error_parts.append(f"Disallowed columns found: {sorted(list(extra))}")
        
        raise ValueError(f"SQL script does not match required format. {'. '.join(error_parts)}")


# ========================================================================================
# STATISTICS OPERATIONS
# ========================================================================================

def get_script_count(db) -> int:
    """Get the total number of SQL scripts."""
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM dq.dq_sql_scripts")
            return cursor.fetchone()[0]
    except Exception as e:
        print(f"Error getting script count: {str(e)}")
        return 0


def get_bad_detail_count(db) -> int:
    """Get the total number of records in the bad_detail table."""
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM dq.bad_detail")
            return cursor.fetchone()[0]
    except Exception as e:
        print(f"Error getting bad_detail count: {str(e)}")
        return 0


# ========================================================================================
# SQL SCRIPT MANAGEMENT
# ========================================================================================

def get_sql_scripts(db) -> List[Dict[str, Any]]:
    """Get all saved SQL scripts from the database."""
    cursor = None
    try:
        cursor = db.cursor()
        query = "SELECT id, name, description, content, created_at, updated_at FROM DQ.dq_sql_scripts ORDER BY id ASC;"
        cursor.execute(query)
        
        fetched_rows = cursor.fetchall()
        
        if not cursor.description:
            return []

        column_names = [desc[0] for desc in cursor.description]
        
        if 'id' not in column_names:
            raise ValueError("The 'id' column is missing from the dq_sql_scripts table.")

        id_index = column_names.index('id')
        scripts = []

        for row in fetched_rows:
            if row[id_index] is None:
                continue
            
            script_dict = dict(zip(column_names, row))
            
            if 'id' not in script_dict or script_dict['id'] is None:
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
    """Get a single SQL script by ID."""
    cursor = None
    try:
        cursor = db.cursor()
        cursor.execute(
            "SELECT id, name, description, content, created_at, updated_at FROM dq.dq_sql_scripts WHERE id = %s;",
            (script_id,)
        )
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


def create_sql_script(db, script_data: Dict[str, Any], user=None) -> Dict[str, Any]:
    """Create a new SQL script and its corresponding staging table."""
    # Only validate columns for non-admin users
    if not user or user.role != "admin":
        _validate_sql_script_columns(script_data['content'])
    
    cursor = None
    try:
        cursor = db.cursor()

        # Check for existing script with the same name
        script_name = script_data.get('name')
        if not script_name:
            raise ValueError("Script name cannot be empty.")
        
        cursor.execute("SELECT id FROM dq.dq_sql_scripts WHERE name = %s;", (script_name,))
        if cursor.fetchone():
            raise ValueError(f"A script with the name '{script_name}' already exists.")

        # Insert new script
        current_time = datetime.now()
        query = """
            INSERT INTO dq.dq_sql_scripts (name, description, content, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, name, description, content, created_at, updated_at;
        """
        cursor.execute(query, (
            script_data['name'], 
            script_data.get('description'), 
            script_data['content'], 
            current_time, 
            current_time
        ))
        new_script_tuple = cursor.fetchone()

        if not new_script_tuple:
            raise ValueError("Insert operation did not return the new script.")

        if cursor.description is None:
            raise ValueError("cursor.description is None after fetching a new script.")

        column_names = [desc[0] for desc in cursor.description]
        
        try:
            id_index = column_names.index('id')
        except ValueError:
            raise ValueError("Fatal: 'id' column not found in RETURNING clause result.") from None

        new_id = new_script_tuple[id_index]

        if not new_id:
            raise ValueError("Failed to retrieve ID for the newly created script (database returned NULL).")

        new_script_dict = _process_result_row(new_script_tuple, column_names)

        # Create the corresponding staging table
        _create_staging_table(cursor, new_id, script_data['content'])

        db.commit()
        return new_script_dict

    except (KeyError, psycopg2.Error, ValueError) as e:
        if db and not getattr(db, 'closed', True): 
            db.rollback()
        if isinstance(e, KeyError):
            raise ValueError(f"Missing required script data: {str(e)}") from e
        raise
    except Exception as e:
        if db and not getattr(db, 'closed', True): 
            db.rollback()
        raise RuntimeError(f"An unexpected issue occurred in create_sql_script: {str(e)}") from e
    finally:
        if cursor:
            cursor.close()


def _create_staging_table(cursor, script_id: int, script_content: str):
    """Create a staging table for a script."""
    stg_table_name_str = _get_stg_table_name_str(script_id)
    
    # Drop if it exists
    drop_table_query = f"DROP TABLE IF EXISTS stg.{stg_table_name_str};"
    cursor.execute(drop_table_query)

    # Clean script content
    clean_script_content = script_content.strip()
    if clean_script_content.endswith(';'):
        clean_script_content = clean_script_content[:-1]

    # Create the table
    create_table_query = f"CREATE TABLE stg.{stg_table_name_str} AS ({clean_script_content}) WITH NO DATA;"
    cursor.execute(create_table_query)


def update_sql_script(db, script_id: int, script_data: Dict[str, Any], user=None) -> Optional[Dict[str, Any]]:
    """Update an existing SQL script after validating its new content."""
    _validate_sql_script_columns(script_data['content'])

    cursor = None
    try:
        cursor = db.cursor()
        name = script_data['name']

        # Check if another script with the same name exists
        cursor.execute("SELECT id FROM dq.dq_sql_scripts WHERE name = %s AND id != %s;", (name, script_id))
        if cursor.fetchone():
            raise ValueError(f"Another script with the name '{name}' already exists.")
        
        description = script_data.get('description')
        content = script_data['content']
        current_time = datetime.now()

        query = """
            UPDATE dq.dq_sql_scripts
            SET name = %s, description = %s, content = %s, updated_at = %s
            WHERE id = %s
            RETURNING id, name, description, content, created_at, updated_at;
        """
        cursor.execute(query, (name, description, content, current_time, script_id))
        updated_script_tuple = cursor.fetchone()

        if not updated_script_tuple:
            return None 

        db.commit()

        if cursor.description is None:
             raise ValueError("cursor.description is None after fetching updated script.")
        
        column_names = [desc[0] for desc in cursor.description]
        return _process_result_row(updated_script_tuple, column_names)
    
    except (KeyError, psycopg2.Error, ValueError) as e:
        if db and not getattr(db, 'closed', True): 
            db.rollback()
        if isinstance(e, KeyError):
            raise ValueError(f"Missing required script data for update: {str(e)}") from e
        raise
    except Exception as e:
        if db and not getattr(db, 'closed', True): 
            db.rollback()
        raise RuntimeError(f"An unexpected issue occurred in update_sql_script: {str(e)}") from e
    finally:
        if cursor:
            cursor.close()


def delete_sql_script(db, script_id: int) -> Dict[str, Any]:
    """Delete a SQL script and its staging table."""
    cursor = None
    try:
        cursor = db.cursor()

        # Drop the corresponding staging table
        stg_table_name_str = _get_stg_table_name_str(script_id)
        drop_table_query = f"DROP TABLE IF EXISTS stg.{stg_table_name_str};"
        cursor.execute(drop_table_query)

        cursor.execute("DELETE FROM dq.dq_sql_scripts WHERE id = %s;", (script_id,))
        deleted_rows = cursor.rowcount
        
        db.commit()
        
        if deleted_rows == 0:
            return {"success": False, "message": "Script not found or already deleted.", "deleted_rows": 0}
        return {"success": True, "deleted_rows": deleted_rows}
    except Exception:
        if db: 
            db.rollback()
        raise
    finally:
        if cursor: 
            cursor.close()


def populate_script_result_table(db, script_id: int) -> Dict[str, Any]:
    """Execute a SQL script and insert the results into its dedicated staging table."""
    cursor = None
    try:
        # Get the script content
        script_info = get_sql_script(db, script_id)
        if not script_info or 'content' not in script_info:
            raise ValueError(f"Script with ID {script_id} not found.")
        
        script_content = script_info['content']
        stg_table_name_str = _get_stg_table_name_str(script_id)
        
        clean_script_content = script_content.strip()
        if clean_script_content.endswith(';'):
            clean_script_content = clean_script_content[:-1]

        cursor = db.cursor()

        # Ensure the staging table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = %s AND table_name = %s
            )
        """, ('stg', stg_table_name_str))
        table_exists = cursor.fetchone()[0]

        if not table_exists:
            create_table_query = f"CREATE TABLE stg.{stg_table_name_str} AS ({clean_script_content}) WITH NO DATA;"
            cursor.execute(create_table_query)
        else:
            truncate_query = f"TRUNCATE TABLE stg.{stg_table_name_str};"
            cursor.execute(truncate_query)

        # Insert data
        insert_query = f"INSERT INTO stg.{stg_table_name_str} {clean_script_content};"
        cursor.execute(insert_query)
        inserted_rows = cursor.rowcount
        
        db.commit()
        
        return {"success": True, "inserted_rows": inserted_rows, "table": f"stg.{stg_table_name_str}"}

    except Exception:
        if db: 
            db.rollback()
        raise
    finally:
        if cursor: 
            cursor.close()


def publish_script_results(db, script_id: int) -> Dict[str, Any]:
    """Publish results from a script's staging table to the central dq.bad_detail table."""
    cursor = None
    stg_table_name_str = _get_stg_table_name_str(script_id)
    
    try:
        cursor = db.cursor()

        # Get distinct (rule_id, source_id) pairs from the staging table
        get_keys_query = f"SELECT DISTINCT rule_id, source_id FROM stg.{stg_table_name_str};"
        cursor.execute(get_keys_query)
        keys_to_replace = cursor.fetchall()

        if not keys_to_replace:
            return {"success": True, "message": "Staging table is empty. Nothing to publish.", "published_rows": 0}
        
        # Delete existing records
        delete_query = "DELETE FROM DQ.bad_detail WHERE (rule_id, source_id) IN %s;"
        cursor.execute(delete_query, (tuple(keys_to_replace),))

        # Insert new records
        insert_query = f"""
            INSERT INTO DQ.bad_detail (rule_id, source_id, source_uid, data_value, txn_date)
            SELECT rule_id, source_id, source_uid, data_value, txn_date
            FROM stg.{stg_table_name_str};
        """
        cursor.execute(insert_query)
        published_rows = cursor.rowcount

        db.commit()

        return {"success": True, "published_rows": published_rows, "keys_replaced_count": len(keys_to_replace)}

    except Exception:
        if db: 
            db.rollback()
        raise
    finally:
        if cursor: 
            cursor.close()


# ========================================================================================
# SCHEDULE MANAGEMENT
# ========================================================================================

def create_schedule(db, schedule: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new schedule."""
    cursor = None
    try:
        cursor = db.cursor()
        query = """
            INSERT INTO dq.dq_schedules (job_name, script_id, cron_schedule, is_active, auto_publish)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, job_name, script_id, cron_schedule, is_active, auto_publish, created_at, updated_at;
        """
        cursor.execute(query, (
            schedule['job_name'],
            schedule['script_id'],
            schedule['cron_schedule'],
            schedule.get('is_active', True),
            schedule.get('auto_publish', False)
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
    """Get all schedules."""
    cursor = None
    try:
        cursor = db.cursor()
        query = """
            SELECT s.id, s.job_name, s.script_id, sc.name as script_name, s.cron_schedule, s.is_active, s.auto_publish, s.created_at, s.updated_at 
            FROM dq.dq_schedules s 
            JOIN dq.dq_sql_scripts sc ON s.script_id = sc.id 
            ORDER BY s.id ASC;
        """
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
    """Get a single schedule by its ID."""
    cursor = None
    try:
        cursor = db.cursor()
        query = "SELECT id, job_name, script_id, cron_schedule, is_active, auto_publish, created_at, updated_at FROM dq.dq_schedules WHERE id = %s;"
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
    """Update an existing schedule."""
    cursor = None
    try:
        cursor = db.cursor()

        # Build dynamic SET clause
        set_parts = []
        values = []
        for key, value in schedule_data.items():
            if value is not None:
                set_parts.append(f"{key} = %s")
                values.append(value)

        if not set_parts:
            return get_schedule(db, schedule_id)

        values.append(schedule_id)
        set_clause = ', '.join(set_parts)

        query = f"UPDATE dq.dq_schedules SET {set_clause} WHERE id = %s RETURNING id, job_name, script_id, cron_schedule, is_active, auto_publish, created_at, updated_at;"

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
    """Delete a schedule."""
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


# ========================================================================================
# USER ACTIONS LOG OPERATIONS
# ========================================================================================

def log_user_action(db, user_id: int, username: str, action: str, 
                   resource_type: Optional[str] = None, resource_id: Optional[int] = None, 
                   details: Optional[dict] = None, user_agent: Optional[str] = None) -> Dict[str, Any]:
    """Log a user action for audit purposes."""
    try:
        cursor = db.cursor()
        
        insert_query = """
            INSERT INTO dq.user_actions_log 
            (user_id, username, action, resource_type, resource_id, details, user_agent)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, created_at;
        """
        
        details_json = json.dumps(details) if details else None
        
        cursor.execute(insert_query, (
            user_id, username, action, resource_type, resource_id,
            details_json, user_agent
        ))
        
        result = cursor.fetchone()
        db.commit()
        
        return {
            "success": True,
            "log_id": result[0],
            "created_at": result[1]
        }
        
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}

def get_user_actions_log(db, limit: int = 100, offset: int = 0, 
                        user_id: Optional[int] = None, action: Optional[str] = None,
                        filters: Optional[dict] = None,
                        get_unique_usernames: bool = False,
                        get_unique_actions: bool = False,
                        get_unique_resource_types: bool = False) -> Dict[str, Any]:
    """Get user actions log with optional filtering and unique values for dropdowns."""
    try:
        cursor = db.cursor()
        
        # Handle unique value requests
        if get_unique_usernames:
            cursor.execute("SELECT DISTINCT username FROM dq.user_actions_log ORDER BY username")
            return {"usernames": [row[0] for row in cursor.fetchall()]}
            
        if get_unique_actions:
            cursor.execute("SELECT DISTINCT action FROM dq.user_actions_log ORDER BY action")
            return {"actions": [row[0] for row in cursor.fetchall()]}
            
        if get_unique_resource_types:
            cursor.execute("SELECT DISTINCT resource_type FROM dq.user_actions_log WHERE resource_type IS NOT NULL ORDER BY resource_type")
            return {"resource_types": [row[0] for row in cursor.fetchall()]}
        
        # Build query for logs
        base_query = """
            SELECT id, user_id, username, action, resource_type, resource_id, 
                   details, user_agent, created_at
            FROM dq.user_actions_log
        """
        
        count_query = "SELECT COUNT(*) FROM dq.user_actions_log"
        
        conditions = []
        params = []
        
        # Legacy filters
        if user_id:
            conditions.append("user_id = %s")
            params.append(user_id)
            
        if action:
            conditions.append("action = %s")
            params.append(action)
        
        # New filters from dict
        if filters:
            if filters.get('username'):
                conditions.append("username ILIKE %s")
                params.append(f"%{filters['username']}%")
                
            if filters.get('action'):
                conditions.append("action = %s")
                params.append(filters['action'])
                
            if filters.get('resource_type'):
                conditions.append("resource_type = %s")
                params.append(filters['resource_type'])
                
            if filters.get('date_from'):
                conditions.append("created_at >= %s")
                params.append(filters['date_from'])
                
            if filters.get('date_to'):
                conditions.append("created_at <= %s")
                params.append(filters['date_to'] + ' 23:59:59')
            
        where_clause = ""
        if conditions:
            where_clause = " WHERE " + " AND ".join(conditions)
            
        # Get total count
        cursor.execute(count_query + where_clause, params)
        total_count = cursor.fetchone()[0]
        
        # Get logs
        base_query += where_clause + " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        cursor.execute(base_query, params)
        results = cursor.fetchall()
        
        logs = [
            {
                "id": row[0],
                "user_id": row[1],
                "username": row[2],
                "action": row[3],
                "resource_type": row[4],
                "resource_id": row[5],
                "details": row[6] if row[6] else None,  # JSONB is already deserialized
                "user_agent": row[7],
                "created_at": row[8]
            }
            for row in results
        ]
        
        return {
            "logs": logs,
            "total_count": total_count
        }
        
    except Exception as e:
        # Log error but return empty result to avoid breaking the application
        print(f"Error in get_user_actions_log: {e}")
        return {"logs": [], "total_count": 0}

# ========================================================================================
# SCHEDULE RUN LOG OPERATIONS
# ========================================================================================

def get_schedule_run_logs(db, limit: int = 100, offset: int = 0, 
                         schedule_id: Optional[int] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get schedule run logs with optional filtering."""
    try:
        cursor = db.cursor()
        
        base_query = """
            SELECT id, schedule_id, job_name, script_id, script_name, status,
                   started_at, completed_at, duration_seconds, rows_affected,
                   error_message, auto_published, created_by_user_id
            FROM dq.schedule_run_log
        """
        
        conditions = []
        params = []
        
        if schedule_id:
            conditions.append("schedule_id = %s")
            params.append(schedule_id)
            
        if status:
            conditions.append("status = %s")
            params.append(status)
            
        if conditions:
            base_query += " WHERE " + " AND ".join(conditions)
            
        base_query += " ORDER BY started_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        cursor.execute(base_query, params)
        results = cursor.fetchall()
        
        return [
            {
                "id": row[0],
                "schedule_id": row[1],
                "job_name": row[2],
                "script_id": row[3],
                "script_name": row[4],
                "status": row[5],
                "started_at": row[6],
                "completed_at": row[7],
                "duration_seconds": row[8],
                "rows_affected": row[9],
                "error_message": row[10],
                "auto_published": row[11],
                "created_by_user_id": row[12]
            }
            for row in results
        ]
        
    except Exception as e:
        return []


# ========================================================================================
# QUERY EXECUTION
# ========================================================================================

def execute_query(query: str, db, params: Optional[List[Any]] = None) -> Dict[str, Any]:
    """
    Execute a SQL query and return results in a standardized format.
    
    Args:
        query: SQL query string to execute
        db: Database connection
        params: Optional list of parameters for the query
        
    Returns:
        Dictionary with 'data' key containing list of row dictionaries,
        and 'column_names' key containing list of column names
    """
    cursor = None
    try:
        cursor = db.cursor()
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        # Get column names from cursor description
        column_names = [desc[0] for desc in cursor.description] if cursor.description else []
        
        # Fetch all rows
        rows = cursor.fetchall()
        
        # Process rows into dictionaries
        data = []
        for row in rows:
            data.append(_process_result_row(row, column_names))
        
        return {
            "data": data,
            "column_names": column_names
        }
        
    except psycopg2.Error as db_err:
        raise ValueError(f"Database query failed: {str(db_err)}") from db_err
    except Exception as e:
        raise RuntimeError(f"An unexpected error occurred in execute_query: {str(e)}") from e
    finally:
        if cursor:
            cursor.close()
