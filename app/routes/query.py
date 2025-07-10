from fastapi import APIRouter, Depends, HTTPException
from app.database import get_db
from app import crud
import psycopg2  # For error handling
from pydantic import BaseModel

class QueryRequest(BaseModel):
    query: str

router = APIRouter()

@router.post("/")
def execute_query(request: QueryRequest, db = Depends(get_db)):
    """Execute a custom SQL query (read-only)"""
    query = request.query
    if not query.strip().lower().startswith("select"):
        raise HTTPException(status_code=400, detail="Only SELECT queries are allowed")
    try:
        return crud.execute_query(query, db)
    except psycopg2.Error as e:
        raise HTTPException(status_code=400, detail="Query failed: An error occurred while processing your query.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Query failed: {str(e)}")