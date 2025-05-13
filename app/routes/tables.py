from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas import GenericModel, TableData
from app import crud

router = APIRouter()

@router.get("/", response_model=List[str])
def get_tables(db: Session = Depends(get_db)):
    """Get all tables in the database"""
    return crud.get_table_names(db)

@router.get("/{table_name}/structure")
def get_table_structure(table_name: str, db: Session = Depends(get_db)):
    """Get the structure of a specific table"""
    tables = crud.get_table_names(db)
    if table_name not in tables:
        raise HTTPException(status_code=404, detail="Table not found")
    
    return crud.get_table_structure(table_name, db)

@router.get("/{table_name}/data", response_model=TableData)
def get_table_data(
    table_name: str, 
    skip: int = 0, 
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get data from a specific table with pagination"""
    tables = crud.get_table_names(db)
    if table_name not in tables:
        raise HTTPException(status_code=404, detail="Table not found")
    
    return crud.get_table_data(table_name, skip, limit, db)

@router.post("/{table_name}/data")
def insert_table_data(
    table_name: str, 
    item: GenericModel,
    db: Session = Depends(get_db)
):
    """Insert data into a specific table"""
    tables = crud.get_table_names(db)
    if table_name not in tables:
        raise HTTPException(status_code=404, detail="Table not found")
    
    try:
        return crud.insert_table_data(table_name, item.data, db)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Insert failed: {str(e)}")

@router.put("/{table_name}/data/{record_id}")
def update_table_data(
    table_name: str,
    record_id: int,
    item: GenericModel,
    id_column: str = "id",
    db: Session = Depends(get_db)
):
    """Update data in a specific table by ID"""
    tables = crud.get_table_names(db)
    if table_name not in tables:
        raise HTTPException(status_code=404, detail="Table not found")
    
    try:
        result = crud.update_table_data(table_name, record_id, item.data, id_column, db)
        if result["updated_rows"] == 0:
            raise HTTPException(status_code=404, detail=f"Record with ID {record_id} not found")
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Update failed: {str(e)}")

@router.delete("/{table_name}/data/{record_id}")
def delete_table_data(
    table_name: str,
    record_id: int,
    id_column: str = "id",
    db: Session = Depends(get_db)
):
    """Delete data from a specific table by ID"""
    tables = crud.get_table_names(db)
    if table_name not in tables:
        raise HTTPException(status_code=404, detail="Table not found")
    
    try:
        result = crud.delete_table_data(table_name, record_id, id_column, db)
        if result["deleted_rows"] == 0:
            raise HTTPException(status_code=404, detail=f"Record with ID {record_id} not found")
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Delete failed: {str(e)}")