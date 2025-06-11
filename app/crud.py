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

class TableStructureValidationError(ValueError):
    """Exception raised when table structure validation fails."""
    pass

def _validate_table_structure(db: Session, table_name: str, is_temporary: bool):
    """Validate that a table has the required structure, accounting for temporary tables."""
    # 'table_name' here is the base name.
    # 'is_temporary' refers to the SQL TEMPORARY keyword.
    
    schema_to_check = None
    if is_temporary:
        # For true SQL TEMPORARY tables, they reside in a pg_temp_X schema.
        # We need to find if ANY such temp table with that name has the columns.
        # This assumes the table name is unique across temp schemas for the session,
        # or we are checking the one created by the current session.
        val_sql = text("""
        SELECT COUNT(c.column_name)
        FROM information_schema.columns c
        JOIN information_schema.tables t ON c.table_name = t.table_name AND c.table_schema = t.table_schema
        WHERE t.table_name = :table_name
          AND t.table_schema LIKE 'pg_temp_%' 
          AND c.column_name IN ('rule_id', 'source_id', 'source_uid', 'data_value', 'txn_date')
        """)
        validation_result = db.execute(val_sql, {"table_name": table_name}).scalar_one_or_none() or 0
        schema_to_check = "pg_temp_%"
    else: # Permanent table, should be in STG schema for this validation path
        val_sql = text("""
        SELECT COUNT(*) as column_count
        FROM information_schema.columns 
        WHERE table_schema = 'STG' 
          AND table_name = :table_name
          AND column_name IN ('rule_id', 'source_id', 'source_uid', 'data_value', 'txn_date')
        """)
        validation_result = db.execute(val_sql, {"table_name": table_name}).scalar_one_or_none() or 0
        schema_to_check = "STG"
    
    if validation_result != 5:
        raise TableStructureValidationError(
            f"Table '{table_name}' in schema context '{schema_to_check}' (SQL TEMPORARY: {is_temporary}) "
            "structure validation failed. Required columns: rule_id, source_id, source_uid, data_value, txn_date. "
            f"Found {validation_result} matching columns."
        )

def _parse_create_table_statement(script_content: str) -> Optional[Dict[str, Any]]:
    """Parses a CREATE TABLE statement into its components."""
    import re
    pattern = re.compile(
        r"(CREATE\s+(TEMPORARY\s+)?)(TABLE\s+)(IF\s+NOT\s+EXISTS\s+)?(STG\.)?(\w+)(.*)", # Fixed escape characters
        re.IGNORECASE | re.DOTALL
    )
    match = pattern.match(script_content.strip())
    if not match:
        return None
    
    return {
        "full_match": match.group(0),
        "create_kw_full": match.group(1),
        "is_temporary_kw": match.group(2),
        "table_keyword": match.group(3),
        "if_not_exists_kw": match.group(4) or "",
        "current_schema_prefix": match.group(5) or "",
        "base_table_name": match.group(6),
        "rest_of_statement": match.group(7).strip()
    }

def _determine_column_injection_necessity(parsed_info: Dict[str, Any]) -> bool:
    """Determines if STG columns need to be injected."""
    rest_of_statement = parsed_info["rest_of_statement"]
    script_lower_for_col_check = rest_of_statement.lower()
    cols_defined_in_script = False

    if rest_of_statement.startswith("("):
        paren_level = 0
        col_def_content = ""
        for i, char_code in enumerate(rest_of_statement):
            if i == 0: continue
            if char_code == '(': paren_level +=1
            elif char_code == ')':
                if paren_level == 0:
                    col_def_content = rest_of_statement[1:i]
                    break
                paren_level -=1
        if col_def_content.strip():
            cols_defined_in_script = True
            script_lower_for_col_check = col_def_content.lower()
            
    if " as " in rest_of_statement.lower() and not cols_defined_in_script:
         script_lower_for_col_check = "" # Force column addition

    return "rule_id" not in script_lower_for_col_check or "source_id" not in script_lower_for_col_check

def _inject_stg_columns(parsed_info: Dict[str, Any], ddl_table_name_part: str) -> str:
    """Injects STG columns into the CREATE TABLE statement."""
    stg_columns_sql = "rule_id VARCHAR(20), source_id VARCHAR(20), source_uid VARCHAR(500), data_value VARCHAR(2000), txn_date DATE"
    
    create_kw_full = parsed_info["create_kw_full"]
    table_keyword = parsed_info["table_keyword"]
    if_not_exists_kw = parsed_info["if_not_exists_kw"]
    rest_of_statement = parsed_info["rest_of_statement"]

    if rest_of_statement.startswith("("):
        paren_level = 0
        col_def_end_idx = -1
        for idx, char_code in enumerate(rest_of_statement):
            if char_code == '(': paren_level +=1
            elif char_code == ')': 
                paren_level -=1
                if paren_level == 0 and idx > 0:
                    col_def_end_idx = idx
                    break
        
        if col_def_end_idx != -1:
            existing_cols_content = rest_of_statement[1:col_def_end_idx].strip()
            after_col_defs = rest_of_statement[col_def_end_idx+1:].strip()
            new_columns_part = f"({stg_columns_sql}, {existing_cols_content})" if existing_cols_content else f"({stg_columns_sql})"
            return f"{create_kw_full}{table_keyword}{if_not_exists_kw}{ddl_table_name_part} {new_columns_part} {after_col_defs}"
        return parsed_info["full_match"] # Malformed, return original

    elif " as " in rest_of_statement.lower() or not rest_of_statement or rest_of_statement == ";":
        import re
        as_clause_match = re.search(r"(\s+AS\s+.*)", rest_of_statement, re.IGNORECASE | re.DOTALL) # Fixed escape characters
        if as_clause_match:
            as_part = as_clause_match.group(1)
            return f"{create_kw_full}{table_keyword}{if_not_exists_kw}{ddl_table_name_part} ({stg_columns_sql}){as_part}"
        else:
            ending = ";" if rest_of_statement.endswith(";") else ""
            return f"{create_kw_full}{table_keyword}{if_not_exists_kw}{ddl_table_name_part} ({stg_columns_sql}){ending}"
    
    return parsed_info["full_match"] # Unknown structure, return original

def _check_and_modify_table_structure(script_content: str) -> tuple[str, Optional[str], bool]:
    """
    Processes CREATE TABLE statements.
    If a table is explicitly defined in 'STG' schema (e.g., CREATE TABLE STG.foo),
    it ensures the table has the required 5 STG columns.
    Returns: (modified_script_content, base_table_name_for_stg_validation, is_sql_temporary_keyword_used)
    - base_table_name_for_stg_validation: The base name if it's an STG candidate, else None.
    - is_sql_temporary_keyword_used: True if SQL 'TEMPORARY' keyword was in the DDL.
    """
    parsed_info = _parse_create_table_statement(script_content)
    if not parsed_info:
        return script_content, None, False # Not a CREATE TABLE or parse failed

    is_sql_temporary_keyword_used = bool(parsed_info["is_temporary_kw"])
    # Check if 'STG.' was literally in the CREATE TABLE statement for the table name.
    is_explicitly_stg_schema = parsed_info["current_schema_prefix"].upper() == "STG."
    base_table_name = parsed_info["base_table_name"]

    stg_base_name_for_validation = None
    final_script_content = script_content # Default to original

    if is_explicitly_stg_schema:
        # This table is an STG candidate because it's explicitly STG.foo or STG.bar
        stg_base_name_for_validation = base_table_name
        
        # The ddl_table_name_part for injection must include the STG. prefix
        # as _inject_stg_columns reconstructs using this.
        # parsed_info["current_schema_prefix"] will be "STG." or "stg."
        ddl_name_for_injection = parsed_info["current_schema_prefix"] + base_table_name

        if _determine_column_injection_necessity(parsed_info): # parsed_info contains original "rest_of_statement"
            final_script_content = _inject_stg_columns(parsed_info, ddl_name_for_injection)
        # No 'else if needs_reconstruction_for_name' is needed here because if is_explicitly_stg_schema,
        # the name in DDL already includes "STG.", so no reconstruction for name part itself, only for columns.
    # else: Not an explicit STG schema table (e.g. CREATE TABLE foo, CREATE TEMPORARY TABLE bar).
    # These are not STG candidates for column modification according to the new rule.
    # So, no modifications, and stg_base_name_for_validation remains None.

    return final_script_content, stg_base_name_for_validation, is_sql_temporary_keyword_used

def _handle_ddl_dml(db: Session, sql: Any, table_name_to_validate: Optional[str], is_sql_temporary_table: bool) -> Dict[str, Any]:
    """Handles DDL/DML operations with transaction management and STG validation."""
    active_transaction = db.in_transaction()
    if not active_transaction:
        db.begin()

    try:
        result = db.execute(sql)
        # 'table_name_to_validate' is the base name of an explicit STG table.
        # 'is_sql_temporary_table' indicates if TEMPORARY keyword was used for it.
        if table_name_to_validate: # This means it was an explicit STG table
            _validate_table_structure(db, table_name_to_validate, is_sql_temporary_table)
        
        if not active_transaction:
            db.commit()
        # else: outer transaction handles commit/rollback

        return {
            "message": "Statement executed successfully",
            "affected_rows": result.rowcount if result and hasattr(result, 'rowcount') else 0,
            "data": []
        }
    except Exception as e:
        if not active_transaction:
            db.rollback()
        print(f"SQL Error (transaction status: {'rolled back by this handler' if not active_transaction else 'outer transaction active'}): {str(e)}")
        raise

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

    print(f"Original SQL script: {script_content[:200]}...")

    processed_script_content = script_content.strip()
    # Trailing semicolons are generally fine for PostgreSQL with text(), so no need to strip aggressively.

    table_name_for_stg_validation = None
    is_temporary_stg_candidate = False
    
    if "CREATE " in processed_script_content.upper() and "TABLE " in processed_script_content.upper():
        modified_script, stg_base_table_name, is_temp = _check_and_modify_table_structure(processed_script_content)
        if stg_base_table_name: 
            if modified_script != processed_script_content:
                 print(f"Script modified for STG compliance. New: {modified_script[:200]}...")
            processed_script_content = modified_script
            table_name_for_stg_validation = stg_base_table_name
            is_temporary_stg_candidate = is_temp
            
    sql = text(processed_script_content)
    
    # Determine if DDL/DML based on keywords in the potentially modified script
    # This check could be more sophisticated (e.g., using SQLAlchemy's SQL parser if available/performant)
    is_ddl_dml = any(keyword in processed_script_content.upper() for keyword in 
                     ["INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP", "TRUNCATE"])

    try:
        if is_ddl_dml:
            return _handle_ddl_dml(db, sql, table_name_for_stg_validation, is_temporary_stg_candidate)
        else: # Assumed SELECT
            return _handle_select(db, sql)
    except TableStructureValidationError as ve:
        print(f"Table Structure Validation Error: {str(ve)}")
        # The transaction in _handle_ddl_dml should have rolled back.
        raise 
    except Exception as e:
        import traceback
        print(f"SQL Execution Error: {str(e)}")
        print(traceback.format_exc())
        # If an error occurs outside _handle_ddl_dml's explicit transaction (e.g., in _handle_select, or before)
        # and if FastAPI's get_db created a transaction, that might need a rollback.
        # However, typical FastAPI setup with `yield db; db.close()` doesn't auto-rollback on exceptions within the route.
        # The safest is to ensure _handle_ddl_dml handles its own, and SELECTs are read-only.
        # Re-raising a generic ValueError for the route.
        raise ValueError(f"SQL Error: {str(e)}")