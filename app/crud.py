from sqlalchemy import Table, inspect, text
from sqlalchemy.orm import Session
from app.database import metadata, engine
from app import models
from app.schemas import SQLScriptCreate
from typing import List, Dict, Any, Optional
import json
from datetime import datetime, date
from decimal import Decimal
import re

def get_table_names(db: Session):
    """Get all tables in the database"""
    inspector = inspect(engine)
    return inspector.get_table_names()

def get_table_structure(table_name: str, db: Session):
    """Get the structure of a specific table"""
    inspector = inspect(engine)
    return {"columns": inspector.get_columns(table_name)}

def get_table_data(table_name: str, skip: int, limit: int, db: Session):
    """Get data from a specific table with pagination"""
    # Dynamically create table object
    table = Table(table_name, metadata, autoload_with=engine)
    
    # Execute query
    result = db.execute(table.select().offset(skip).limit(limit)).fetchall()
    
    # Convert to list of dicts
    data = []
    for row in result:
        data.append({column.name: value for column, value in zip(table.columns, row)})
    
    return {"data": data, "total": db.execute(table.select().count()).scalar(), "skip": skip, "limit": limit}

def insert_table_data(table_name: str, data: dict, db: Session):
    """Insert data into a specific table"""
    table = Table(table_name, metadata, autoload_with=engine)
    result = db.execute(table.insert().values(**data))
    db.commit()
    return {"success": True, "id": result.inserted_primary_key}

def update_table_data(table_name: str, record_id: int, data: dict, id_column: str, db: Session):
    """Update data in a specific table by ID"""
    table = Table(table_name, metadata, autoload_with=engine)
    result = db.execute(
        table.update()
        .where(table.c[id_column] == record_id)
        .values(**data)
    )
    db.commit()
    return {"success": True, "updated_rows": result.rowcount}

def delete_table_data(table_name: str, record_id: int, id_column: str, db: Session):
    """Delete data from a specific table by ID"""
    table = Table(table_name, metadata, autoload_with=engine)
    result = db.execute(
        table.delete().where(table.c[id_column] == record_id)
    )
    db.commit()
    return {"success": True, "deleted_rows": result.rowcount}

def execute_query(query: str, db: Session):
    """Execute a custom SQL query"""
    result = db.execute(query).fetchall()
    column_names = db.execute(query).keys()
    data = [dict(zip(column_names, row)) for row in result]
    return {"data": data, "count": len(data)}

def get_sql_scripts(db: Session) -> List[models.SQLScript]:
    """Get all SQL scripts"""
    return db.query(models.SQLScript).all()

def get_sql_script(db: Session, script_id: int) -> models.SQLScript:
    """Get a specific SQL script by ID"""
    return db.query(models.SQLScript).filter(models.SQLScript.id == script_id).first()

def create_sql_script(db: Session, script: SQLScriptCreate) -> models.SQLScript:
    """Create a new SQL script"""
    db_script = models.SQLScript(
        name=script.name,
        description=script.description,
        content=script.content
    )
    db.add(db_script)
    db.commit()
    db.refresh(db_script)
    return db_script

def update_sql_script(db: Session, script_id: int, script: SQLScriptCreate) -> models.SQLScript:
    """Update an existing SQL script"""
    db_script = db.query(models.SQLScript).filter(models.SQLScript.id == script_id).first()
    db_script.name = script.name
    db_script.description = script.description
    db_script.content = script.content
    db.commit()
    db.refresh(db_script)
    return db_script

def delete_sql_script(db: Session, script_id: int) -> None:
    """Delete a SQL script"""
    db_script = db.query(models.SQLScript).filter(models.SQLScript.id == script_id).first()
    db.delete(db_script)
    db.commit()

import json
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict, List

# Custom JSON encoder to handle special data types
class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, bytes):
            return obj.hex()
        return json.JSONEncoder.default(self, obj)

def _format_value_for_json(value: Any) -> Any:
    """Format a database value for JSON serialization"""
    if value is None:
        return None
        
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    elif isinstance(value, Decimal):
        return float(value)
    elif isinstance(value, (bytes, bytearray)):
        return value.hex()
        
    # Handle more complex data types
    try:
        # Verify JSON serialization works
        json.dumps(value, cls=JSONEncoder)
        return value
    except (TypeError, OverflowError):
        # If not serializable, convert to string
        return str(value)

def _process_result_row(row: tuple, column_names: List[str]) -> Dict[str, Any]:
    """Process a single row of SQL query results"""
    row_dict = {}
    for idx, column in enumerate(column_names):
        row_dict[column] = _format_value_for_json(row[idx])
    return row_dict

def _check_and_modify_table_structure(script_content: str):
    """Check if the script creates a table in STG schema and ensure it has the required structure"""
    import re
    create_table_pattern = r"CREATE\s+(?:TEMPORARY\s+)?TABLE\s+(?:STG\.)?(\w+)"
    match = re.search(create_table_pattern, script_content, re.IGNORECASE)
    
    if not match:
        return script_content, None
    
    # Get the table name
    table_name = match.group(1)
    
    # Required columns definition
    required_columns = """
    rule_id varchar(20),
    source_id varchar(20),
    source_uid varchar(500),
    data_value varchar(2000),
    txn_date date
    """
    
    # If there's no clear column definition, ensure the structure
    if "rule_id" not in script_content and "source_id" not in script_content:
        # Modify script to include required columns
        script_content = re.sub(
            r"(CREATE\s+(?:TEMPORARY\s+)?TABLE\s+(?:STG\.)?(\w+))(\s*\()?",
            r"\1 (\n" + required_columns + "\n",
            script_content,
            flags=re.IGNORECASE
        )
    
    return script_content, table_name

class TableStructureValidationError(ValueError):
    """Exception raised when table structure validation fails."""
    pass

def _validate_table_structure(db: Session, table_name: str):
    """Validate that a table has the required structure"""
    # Check if table has the required columns
    val_sql = text("""
    SELECT COUNT(*) as column_count
    FROM information_schema.columns 
    WHERE table_schema = 'STG' 
    AND table_name = :table_name
    AND column_name IN ('rule_id', 'source_id', 'source_uid', 'data_value', 'txn_date')
    """)
    
    validation_result = db.execute(val_sql, {"table_name": table_name}).scalar()
    
    if validation_result != 5:
        raise TableStructureValidationError(
            "Table structure validation failed. Required columns: "
            "rule_id varchar(20), source_id varchar(20), source_uid varchar(500), "
            "data_value varchar(2000), txn_date date"
        )

def _handle_ddl_dml(db: Session, sql: Any, table_name_to_validate_stg: Optional[str]) -> Dict[str, Any]:
    """Handles DDL/DML operations with transaction management and STG validation."""
    with db.begin_nested() if db.in_transaction() else db.begin() as trans:
        try:
            result = db.execute(sql)
            # If table_name_to_validate_stg is provided, it means an STG table was created and needs validation.
            if table_name_to_validate_stg:
                _validate_table_structure(db, table_name_to_validate_stg)
            trans.commit()
            return {
                "message": "Statement executed successfully",
                "affected_rows": result.rowcount if hasattr(result, 'rowcount') else 0,
                "data": []
            }
        except Exception as e:
            trans.rollback()
            print(f"SQL Error (transaction rolled back): {str(e)}")
            raise # Re-raise to be caught by the main function

def _handle_select(db: Session, sql: Any) -> Dict[str, Any]:
    """Handles SELECT queries."""
    result = db.execute(sql)
    if result.returns_rows:
        column_names = result.keys()
        rows = result.fetchall()
        data = [_process_result_row(row, column_names) for row in rows]
        return {
            "data": data,
            "count": len(data),
            "message": "Query executed successfully"
        }
    else:
        return {"message": "Query executed, no rows returned", 
                "affected_rows": result.rowcount if hasattr(result, 'rowcount') else 0, 
                "data": []}

def execute_sql_script(db: Session, script_content: str) -> dict:
    """Execute a SQL script and return results"""
    if not script_content or not script_content.strip():
        return {"message": "Empty query", "data": [], "count": 0}

    print(f"Executing SQL script: {script_content[:200]}...")

    processed_script_content = script_content.strip()
    if processed_script_content.endswith(';'):
        processed_script_content = processed_script_content[:-1]

    table_name_for_stg_validation = None
    # Check if it's an STG table creation operation
    is_stg_create_op = "CREATE " in processed_script_content.upper() and \
                       " STG." in processed_script_content.upper()

    if is_stg_create_op:
        # Modify script for STG table and get table name for validation
        processed_script_content, table_name_for_stg_validation = \
            _check_and_modify_table_structure(processed_script_content)
    
    sql = text(processed_script_content)
    # Determine if DDL/DML based on the potentially modified script
    is_ddl_dml = any(keyword in processed_script_content.upper() for keyword in 
                     ["INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP"])

    try:
        if is_ddl_dml:
            # Pass only the table name for STG validation if applicable
            return _handle_ddl_dml(db, sql, table_name_for_stg_validation)
        else:
            return _handle_select(db, sql)
    except TableStructureValidationError as ve:
        print(f"Table Structure Validation Error: {str(ve)}")
        # Rollback should be handled by _handle_ddl_dml if the error originated there
        # or if an outer transaction exists, it might need handling here or by the caller.
        # For simplicity, assuming _handle_ddl_dml's rollback is sufficient for its scope.
        raise # Re-raise to be handled by the route
    except Exception as e:
        import traceback
        print(f"SQL Execution Error: {str(e)}")
        print(traceback.format_exc())
        # Similar to above, rollback handling is tricky for exceptions outside _handle_ddl_dml's transaction.
        # If db.begin() was called implicitly by execute, it might not auto-rollback on Python exception.
        # However, _handle_ddl_dml has its own explicit rollback.
        # For errors in _handle_select or before _handle_ddl_dml's transaction starts,
        # an explicit db.rollback() here might be needed if a session-level transaction was initiated by FastAPI's Depends(get_db).
        # For now, relying on the route's exception handler and _handle_ddl_dml's internal rollback.
        raise ValueError(f"SQL Error: {str(e)}") # Raise a ValueError for the route to catch