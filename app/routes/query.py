from fastapi import APIRouter, Depends, HTTPException
from app.database import get_db
from app import crud
import psycopg2  # For error handling
from psycopg2.extensions import connection as PgConnection  # For type hinting

router = APIRouter()


@router.post("/")
def execute_query(query: str, db: PgConnection = Depends(get_db)):  # Changed type hint
    """Execute a custom SQL query (read-only)"""
    if not query.strip().lower().startswith("select"):
        raise HTTPException(status_code=400, detail="Only SELECT queries are allowed")

    try:
        return crud.execute_query(query, db)
    except psycopg2.Error as e:
        # It's good practice to not expose raw DB error messages directly to the client
        # For debugging, log e.pgerror and e.diag.message_detail if available
        # For the client, a generic message or a sanitized one is better.
        raise HTTPException(status_code=400, detail="Query failed: An error occurred while processing your query.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Query failed: {str(e)}")