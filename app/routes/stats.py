from fastapi import APIRouter, Depends
from app.database import get_db
from app import crud
from psycopg2.extensions import connection as PgConnection

router = APIRouter()

@router.get("/")
def get_stats(db: PgConnection = Depends(get_db)):
    script_count = crud.get_script_count(db)
    bad_detail_count = crud.get_bad_detail_count(db)
    return {"script_count": script_count, "bad_detail_count": bad_detail_count}
