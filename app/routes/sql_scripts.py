from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from app.database import get_db
from app.schemas import SQLScriptCreate, SQLScript
from app import crud

router = APIRouter()

# Model for script execution request
class SQLExecuteRequest(BaseModel):
    script_content: str

@router.get("/", response_model=List[SQLScript])
def get_scripts(db: Session = Depends(get_db)):
    """Get all saved SQL scripts"""
    return crud.get_sql_scripts(db)

@router.get("/{script_id}", response_model=SQLScript)
def get_script(script_id: int, db: Session = Depends(get_db)):
    """Get a specific SQL script by ID"""
    script = crud.get_sql_script(db, script_id)
    if script is None:
        raise HTTPException(status_code=404, detail="SQL script not found")
    return script

@router.post("/", response_model=SQLScript)
def create_script(script: SQLScriptCreate, db: Session = Depends(get_db)):
    """Save a new SQL script"""
    return crud.create_sql_script(db, script)

@router.put("/{script_id}", response_model=SQLScript)
def update_script(script_id: int, script: SQLScriptCreate, db: Session = Depends(get_db)):
    """Update an existing SQL script"""
    existing_script = crud.get_sql_script(db, script_id)
    if existing_script is None:
        raise HTTPException(status_code=404, detail="SQL script not found")
    return crud.update_sql_script(db, script_id, script)

@router.delete("/{script_id}")
def delete_script(script_id: int, db: Session = Depends(get_db)):
    """Delete a SQL script"""
    existing_script = crud.get_sql_script(db, script_id)
    if existing_script is None:
        raise HTTPException(status_code=404, detail="SQL script not found")
    crud.delete_sql_script(db, script_id)
    return {"success": True}

@router.post("/execute")
def execute_script(request: SQLExecuteRequest = Body(...), db: Session = Depends(get_db)):
    """Execute a SQL script and return results"""
    try:
        # Add debug logging
        print(f"Executing script: {request.script_content[:100]}...")
        result = crud.execute_sql_script(db, request.script_content)
        return result
    except Exception as e:
        print(f"Script execution error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Execution failed: {str(e)}")