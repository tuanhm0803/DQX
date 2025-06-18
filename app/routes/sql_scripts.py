from fastapi import APIRouter, Depends, HTTPException, Body
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from app.database import get_db
from app.schemas import SQLScriptCreate, SQLScript
from app import crud
from app.crud import TableStructureValidationError  # Assuming this is still relevant or adapted
import psycopg2  # For error handling
from psycopg2.extensions import connection as PgConnection  # For type hinting

router = APIRouter()

# Constants
SCRIPT_NOT_FOUND = "SQL script not found"


# Model for script execution request
class SQLExecuteRequest(BaseModel):
    script_content: str


@router.get("/", response_model=List[SQLScript])
def get_scripts(db: PgConnection = Depends(get_db)):
    """Get all saved SQL scripts"""
    try:
        scripts_list = crud.get_sql_scripts(db)
        return scripts_list
    except psycopg2.Error as e:
        # Log e for server-side details
        raise HTTPException(status_code=500, detail=f"Database error while retrieving scripts: {str(e)}")
    except ValueError as ve: # Catch specific ValueErrors from CRUD, e.g., if table structure is unexpected
        # Log ve for server-side details
        raise HTTPException(status_code=500, detail=f"Error processing script data: {str(ve)}")
    except Exception as e:
        # Log e for server-side details
        raise HTTPException(status_code=500, detail="An unexpected server error occurred while retrieving scripts.")


@router.get("/{script_id}", response_model=SQLScript)
def get_script(script_id: int, db: PgConnection = Depends(get_db)):  # Changed type hint
    """Get a specific SQL script by ID"""
    try:
        script = crud.get_sql_script(db, script_id)
        if script is None:
            raise HTTPException(status_code=404, detail=SCRIPT_NOT_FOUND)
        return script
    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve script {script_id}: {str(e)}")
    except HTTPException:  # Re-raise if it's already an HTTPException (like 404)
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


@router.post("/", response_model=SQLScript)
def create_script(script: SQLScriptCreate, db: PgConnection = Depends(get_db)):
    """Save a new SQL script"""
    try:
        created_script_dict = crud.create_sql_script(db, script.model_dump())
        return created_script_dict
    except psycopg2.Error as e:
        if db and not getattr(db, 'closed', True): db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error while creating script: {str(e)}")
    except ValueError as ve:  # Catch specific ValueErrors from CRUD
        if db and not getattr(db, 'closed', True): db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to create script: {str(ve)}")
    except Exception as e:
        if db and not getattr(db, 'closed', True): db.rollback()
        # Consider logging the full exception e here for server-side debugging
        raise HTTPException(status_code=500, detail="An unexpected server error occurred while creating script.")


@router.put("/{script_id}", response_model=SQLScript)
def update_script(script_id: int, script: SQLScriptCreate, db: PgConnection = Depends(get_db)):  # Changed type hint
    """Update an existing SQL script"""
    try:
        existing_script = crud.get_sql_script(db, script_id)  # Check existence first
        if existing_script is None:
            raise HTTPException(status_code=404, detail=SCRIPT_NOT_FOUND)
        # Pass the model as a dictionary, excluding unset values for partial updates
        # For PUT, typically all fields are required, or it's a full replacement.
        # If partial update is desired, PATCH is more appropriate, or model_dump(exclude_unset=True) for PUT.
        # Assuming SQLScriptCreate contains all necessary fields for an update.
        updated_script_dict = crud.update_sql_script(db, script_id, script.model_dump())
        if updated_script_dict is None:  # crud.update_sql_script returns Optional
            raise HTTPException(status_code=404, detail="Update failed or script not found after update attempt.")
        return updated_script_dict
    except psycopg2.Error as e:
        if db and not getattr(db, 'closed', True): db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error while updating script {script_id}: {str(e)}")
    except ValueError as ve:  # Catch specific ValueErrors from CRUD
        if db and not getattr(db, 'closed', True): db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to update script {script_id}: {str(ve)}")
    except HTTPException:  # Re-raise if it's already an HTTPException (like 404)
        raise
    except Exception as e:
        if db and not getattr(db, 'closed', True): db.rollback()
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred while updating script {script_id}.")


@router.delete("/{script_id}")
def delete_script(script_id: int, db: PgConnection = Depends(get_db)):  # Changed type hint
    """Delete a SQL script"""
    try:
        existing_script = crud.get_sql_script(db, script_id)  # Check existence first
        if existing_script is None:
            raise HTTPException(status_code=404, detail=SCRIPT_NOT_FOUND)
        crud.delete_sql_script(db, script_id)
        return {"success": True}
    except psycopg2.Error as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to delete script {script_id}: {str(e)}")
    except HTTPException:  # Re-raise if it's already an HTTPException (like 404)
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"An unexpected error occurred: {str(e)}")


@router.post("/execute")
def execute_script(request: SQLExecuteRequest = Body(...), db: PgConnection = Depends(get_db)):  # Changed type hint
    """Execute a SQL script and return results"""
    try:
        # Add debug logging
        print(f"Executing script: {request.script_content[:100]}...")
        result = crud.execute_sql_script(db, request.script_content)

        # Handle error from CREATE TABLE prevention or other custom errors from crud
        if isinstance(result, dict) and result.get("error") is True:
            # Assuming crud.execute_sql_script might return a dict with an error key
            # and that it doesn't raise an exception itself for this case.
            # If it does raise an exception, this check might be redundant.
            raise HTTPException(status_code=403, detail=result.get("message", "Execution forbidden"))

        return result
    except TableStructureValidationError as e:  # Custom validation error
        print(f"Table structure validation error: {str(e)}")
        # db.rollback() # Typically, validation errors don't involve DB transactions needing rollback
        raise HTTPException(
            status_code=400,
            detail=f"Table Structure Error: {str(e)}. All tables in STG schema must have exactly these columns: rule_id varchar(20), source_id varchar(20), source_uid varchar(500), data_value varchar(2000), txn_date date",
        )
    except psycopg2.Error as e:  # Specific psycopg2 errors
        db.rollback()  # Rollback on database errors
        # Consider logging e.pgcode and e.pgerror for more detailed DB error info
        raise HTTPException(status_code=400, detail=f"Script execution database error: {str(e)}")
    except HTTPException:  # Re-raise if it's already an HTTPException
        raise
    except Exception as e:  # Catch-all for other unexpected errors
        print(f"Script execution unexpected error: {str(e)}")
        db.rollback()  # Rollback on any other error
        raise HTTPException(status_code=400, detail=f"Script execution unexpected error: {str(e)}")


@router.post("/{script_id}/populate_table")
def populate_table(script_id: int, db: PgConnection = Depends(get_db)):
    """Populate the staging table for a specific SQL script"""
    try:
        result = crud.populate_script_result_table(db, script_id)
        return result
    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error while populating table for script {script_id}: {str(e)}")
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=f"Failed to populate table for script {script_id}: {str(ve)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred while populating table for script {script_id}: {str(e)}")


@router.post("/{script_id}/publish")
def publish_results(script_id: int, db: PgConnection = Depends(get_db)):
    """Publish results from the script's staging table to the main bad_detail table."""
    try:
        result = crud.publish_script_results(db, script_id)
        return result
    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error while publishing results for script {script_id}: {str(e)}")
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=f"Failed to publish results for script {script_id}: {str(ve)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred while publishing results for script {script_id}: {str(e)}")