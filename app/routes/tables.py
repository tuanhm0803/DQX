from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.database import get_db
from app.schemas import GenericModel, TableData
from app import crud
import logging
import psycopg2

router = APIRouter()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TABLE_NOT_FOUND_ERROR = "Table not found"

@router.get("/", response_model=List[str])
def get_tables(db = Depends(get_db)):
    """Get all tables in the 'DQ' schema"""
    cursor = None
    try:
        cursor = db.cursor()
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'dq';")
        tables = [row[0] for row in cursor.fetchall()]
        logger.info(f"Tables in 'DQ' schema: {tables}")
        return tables
    except psycopg2.Error as e:
        logger.error(f"Error retrieving tables: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error loading tables: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error retrieving tables: {str(e)}")
        raise HTTPException(status_code=500, detail="Error loading tables")
    finally:
        if cursor:
            cursor.close()

@router.get("/{table_name}/structure")
def get_table_structure(table_name: str, db = Depends(get_db)):
    """Get the structure of a specific table"""
    tables = crud.get_table_names(db)
    if table_name not in tables:
        raise HTTPException(status_code=404, detail=TABLE_NOT_FOUND_ERROR)
    
    return crud.get_table_structure(table_name, db)

@router.get("/{table_name}/data", response_model=TableData)
def get_table_data(
    table_name: str, 
    skip: int = 0, 
    limit: int = 100,
    db = Depends(get_db)
):
    """Get data from a specific table with pagination"""
    tables = crud.get_table_names(db)
    if table_name not in tables:
        raise HTTPException(status_code=404, detail=TABLE_NOT_FOUND_ERROR)
    
    return crud.get_table_data(table_name, skip, limit, db)

@router.post("/{table_name}/data")
def insert_table_data(
    table_name: str, 
    item: GenericModel,
    db = Depends(get_db)
):
    """Insert data into a specific table"""
    tables = crud.get_table_names(db)
    if table_name not in tables:
        raise HTTPException(status_code=404, detail=TABLE_NOT_FOUND_ERROR)
    
    try:
        return crud.insert_table_data(table_name, item.data, db)
    except psycopg2.Error as e:
        logger.error(f"Insert failed for {table_name}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Insert failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error during insert for {table_name}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Insert failed: {str(e)}")


@router.put("/{table_name}/data/{record_id}")
def update_table_data(
    table_name: str,
    record_id: int,
    item: GenericModel,
    id_column: str = "id",
    db = Depends(get_db)
):
    """Update data in a specific table by ID"""
    tables = crud.get_table_names(db)
    if table_name not in tables:
        raise HTTPException(status_code=404, detail=TABLE_NOT_FOUND_ERROR)
    
    try:
        result = crud.update_table_data(table_name, record_id, item.data, id_column, db)
        if result["updated_rows"] == 0:
            raise HTTPException(status_code=404, detail=f"Record with ID {record_id} not found or no data changed")
        return result
    except psycopg2.Error as e:
        logger.error(f"Update failed for {table_name}, record {record_id}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Update failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error during update for {table_name}, record {record_id}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Update failed: {str(e)}")

@router.delete("/{table_name}/data/{record_id}")
def delete_table_data(
    table_name: str,
    record_id: int,
    id_column: str = "id",
    db = Depends(get_db)
):
    """Delete data from a specific table by ID"""
    tables = crud.get_table_names(db)
    if table_name not in tables:
        raise HTTPException(status_code=404, detail=TABLE_NOT_FOUND_ERROR)
    
    try:
        result = crud.delete_table_data(table_name, record_id, id_column, db)
        if result["deleted_rows"] == 0:
            raise HTTPException(status_code=404, detail=f"Record with ID {record_id} not found")
        return result
    except psycopg2.Error as e:
        logger.error(f"Delete failed for {table_name}, record {record_id}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Delete failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error during delete for {table_name}, record {record_id}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Delete failed: {str(e)}")