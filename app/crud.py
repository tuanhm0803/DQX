from sqlalchemy import Table, inspect, text
from sqlalchemy.orm import Session
from app.database import metadata, engine
from app import models
from app.schemas import SQLScriptCreate
from typing import List, Dict, Any
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

def execute_sql_script(db: Session, script_content: str) -> dict:
    """Execute a SQL script and return results"""
    if not script_content or not script_content.strip():
        return {"message": "Empty query", "data": [], "count": 0}
    
    # Strip trailing semicolons which might cause issues
    script_content = script_content.strip()
    if script_content.endswith(';'):
        script_content = script_content[:-1]
    
    # Check and modify table structure if needed
    script_content, table_name = _check_and_modify_table_structure(script_content)
    
    # Use text() to create a textual SQL statement
    sql = text(script_content)
    
    try:
        # Execute the SQL statement
        result = db.execute(sql)
        
        # Check if this is a SELECT query that returns rows
        if result.returns_rows:
            column_names = result.keys()
            rows = result.fetchall()
            
            # Process rows using helper function
            data = [_process_result_row(row, column_names) for row in rows]
            
            return {
                "data": data,
                "count": len(data),
                "message": "Query executed successfully"
            }
        else:
            # For statements that don't return results (INSERT, UPDATE, etc.)
            db.commit()
            
            # If we detected a CREATE TABLE, validate its structure
            if table_name:
                try:
                    _validate_table_structure(db, table_name)
                except TableStructureValidationError as v_err:
                    db.rollback()
                    raise TableStructureValidationError(f"Table structure validation error: {str(v_err)}")
            
            return {
                "message": "Statement executed successfully",
                "affected_rows": result.rowcount,
                "data": []
            }
    except TableStructureValidationError:
        # Re-raise the validation error
        raise
    except Exception as e:
        # Roll back on error
        db.rollback()
        print(f"SQL execution error details: {str(e)}")
        raise ValueError(f"SQL Error: {str(e)}")