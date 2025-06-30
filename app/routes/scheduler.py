from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import List
from app import crud, schemas
from app.database import get_db
from psycopg2.extensions import connection as PgConnection
from app.dependencies import templates, render_template

router = APIRouter()

@router.get("/schedules/", response_class=HTMLResponse)
def list_schedules(request: Request, db: PgConnection = Depends(get_db)):
    schedules = crud.get_schedules(db)
    scripts = crud.get_sql_scripts(db)
    return render_template("scheduler.html", {"request": request, "schedules": schedules, "scripts": scripts, "form_title": "Create New Schedule"})

@router.post("/schedules/")
def create_schedule_form(
    db: PgConnection = Depends(get_db),
    job_name: str = Form(...),
    script_id: int = Form(...),
    schedule_type: str = Form(...),
    day_of_week: str = Form(None),
    execution_time: str = Form(...),
    is_active: bool = Form(False)
):
    time_parts = execution_time.split(':')
    minute, hour = time_parts[1], time_parts[0]
    cron_schedule = f"{minute} {hour} * * *"
    if schedule_type == 'weekly':
        cron_schedule = f"{minute} {hour} * * {day_of_week}"
    elif schedule_type == 'monthly':
        cron_schedule = f"{minute} {hour} L * *"

    schedule_data = schemas.ScheduleCreate(
        job_name=job_name,
        script_id=script_id,
        cron_schedule=cron_schedule,
        is_active=is_active
    )
    try:
        crud.create_schedule(db, schedule_data.model_dump())
    except ValueError as e:
        # You might want to render the form again with an error message
        raise HTTPException(status_code=400, detail=str(e))
    return RedirectResponse(url="/schedules/", status_code=303)

@router.get("/schedules/edit/{schedule_id}", response_class=HTMLResponse)
def edit_schedule_form(schedule_id: int, request: Request, db: PgConnection = Depends(get_db)):
    schedule = crud.get_schedule(db, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    schedules = crud.get_schedules(db)
    scripts = crud.get_sql_scripts(db)
    return render_template("scheduler.html", {"request": request, "schedule": schedule, "schedules": schedules, "scripts": scripts, "form_title": "Edit Schedule"})

@router.get("/schedules/delete/{schedule_id}")
def delete_schedule_form(schedule_id: int, db: PgConnection = Depends(get_db)):
    result = crud.delete_schedule(db, schedule_id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return RedirectResponse(url="/schedules/", status_code=303)

# --- API Endpoints (can be kept for other purposes or removed if not needed) ---

@router.post("/api/schedules/", response_model=schemas.Schedule)
def api_create_schedule(schedule: schemas.ScheduleCreate, db: PgConnection = Depends(get_db)):
    """Create a new schedule."""
    try:
        return crud.create_schedule(db, schedule.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/api/schedules/", response_model=List[schemas.Schedule])
def api_read_schedules(db: PgConnection = Depends(get_db)):
    """Retrieve all schedules."""
    return crud.get_schedules(db)

@router.get("/api/schedules/{schedule_id}", response_model=schemas.Schedule)
def api_read_schedule(schedule_id: int, db: PgConnection = Depends(get_db)):
    """Retrieve a single schedule by ID."""
    db_schedule = crud.get_schedule(db, schedule_id)
    if db_schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return db_schedule

@router.put("/api/schedules/{schedule_id}", response_model=schemas.Schedule)
def api_update_schedule(schedule_id: int, schedule: schemas.ScheduleUpdate, db: PgConnection = Depends(get_db)):
    """Update a schedule."""
    db_schedule = crud.update_schedule(db, schedule_id, schedule.model_dump(exclude_unset=True))
    if db_schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return db_schedule

@router.delete("/api/schedules/{schedule_id}")
def api_delete_schedule(schedule_id: int, db: PgConnection = Depends(get_db)):
    """Delete a schedule."""
    result = crud.delete_schedule(db, schedule_id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return {"message": "Schedule deleted successfully"}
