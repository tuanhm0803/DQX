from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app import crud, schemas
from app.database import get_db
from psycopg2.extensions import connection as PgConnection

router = APIRouter()

@router.post("/", response_model=schemas.Schedule)
def create_schedule(schedule: schemas.ScheduleCreate, db: PgConnection = Depends(get_db)):
    """Create a new schedule."""
    try:
        return crud.create_schedule(db, schedule.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[schemas.Schedule])
def read_schedules(db: PgConnection = Depends(get_db)):
    """Retrieve all schedules."""
    return crud.get_schedules(db)

@router.get("/{schedule_id}", response_model=schemas.Schedule)
def read_schedule(schedule_id: int, db: PgConnection = Depends(get_db)):
    """Retrieve a single schedule by ID."""
    db_schedule = crud.get_schedule(db, schedule_id)
    if db_schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return db_schedule

@router.put("/{schedule_id}", response_model=schemas.Schedule)
def update_schedule(schedule_id: int, schedule: schemas.ScheduleUpdate, db: PgConnection = Depends(get_db)):
    """Update a schedule."""
    db_schedule = crud.update_schedule(db, schedule_id, schedule.model_dump(exclude_unset=True))
    if db_schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return db_schedule

@router.delete("/{schedule_id}")
def delete_schedule(schedule_id: int, db: PgConnection = Depends(get_db)):
    """Delete a schedule."""
    result = crud.delete_schedule(db, schedule_id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return {"message": "Schedule deleted successfully"}
