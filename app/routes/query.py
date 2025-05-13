from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import crud

router = APIRouter()

@router.post("/")
def execute_query(query: str, db: Session = Depends(get_db)):
    """Execute a custom SQL query (read-only)"""
    if not query.strip().lower().startswith("select"):
        raise HTTPException(status_code=400, detail="Only SELECT queries are allowed")
    
    try:
        return crud.execute_query(query, db)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Query failed: {str(e)}")