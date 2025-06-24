from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import List, Optional
from app import crud, schemas
from app.database import get_db
from psycopg2.extensions import connection as PgConnection
from app.dependencies import templates

# Router for API endpoints
api_router = APIRouter()

# Router for HTML pages
page_router = APIRouter()

# --- Page Endpoints ---

@page_router.get("/editor", response_class=HTMLResponse)
async def sql_editor_page(request: Request, script_id: Optional[int] = None, db: PgConnection = Depends(get_db)):
    scripts = crud.get_sql_scripts(db)
    selected_script = None
    if script_id:
        selected_script = crud.get_sql_script(db, script_id)
    return templates.TemplateResponse("sql_editor.html", {
        "request": request, 
        "scripts": scripts, 
        "selected_script": selected_script,
        "results": None,
        "error": None
    })

@page_router.post("/editor/save")
async def save_script_form(
    script_id: Optional[int] = Form(None),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    content: str = Form(...),
    db: PgConnection = Depends(get_db)
):
    script_data = schemas.SQLScriptCreate(name=name, description=description, content=content)
    if script_id:
        crud.update_sql_script(db, script_id, script_data.model_dump())
    else:
        crud.create_sql_script(db, script_data.model_dump())
    return RedirectResponse(url="/editor", status_code=303)

@page_router.post("/editor/execute")
async def execute_script_form(
    request: Request,
    content: str = Form(...),
    db: PgConnection = Depends(get_db)
):
    scripts = crud.get_sql_scripts(db)
    results = None
    error = None
    try:
        query_results = crud.execute_query(content, db)
        if "data" in query_results and "columns" in query_results:
            # Transform the data to the format expected by the template
            results = {
                "headers": query_results["columns"],
                "rows": [list(row.values()) for row in query_results["data"]]
            }
    except Exception as e:
        error = str(e)
    
    # Re-render the editor page with results or an error
    return templates.TemplateResponse("sql_editor.html", {
        "request": request, 
        "scripts": scripts, 
        "selected_script": {"content": content}, # Pass back the executed script
        "results": results,
        "error": error
    })

@page_router.get("/editor/delete/{script_id}")
async def delete_script_form(script_id: int, db: PgConnection = Depends(get_db)):
    crud.delete_sql_script(db, script_id)
    return RedirectResponse(url="/editor", status_code=303)

# --- API Endpoints ---

@api_router.get("/", response_model=List[schemas.SQLScript])
def get_scripts(db: PgConnection = Depends(get_db)):
    return crud.get_sql_scripts(db)

@api_router.get("/{script_id}", response_model=schemas.SQLScript)
def get_script(script_id: int, db: PgConnection = Depends(get_db)):
    script = crud.get_sql_script(db, script_id)
    if script is None:
        raise HTTPException(status_code=404, detail="SQL script not found")
    return script

@api_router.post("/", response_model=schemas.SQLScript)
def create_script(script: schemas.SQLScriptCreate, db: PgConnection = Depends(get_db)):
    return crud.create_sql_script(db, script.model_dump())

@api_router.put("/{script_id}", response_model=schemas.SQLScript)
def update_script(script_id: int, script: schemas.SQLScriptCreate, db: PgConnection = Depends(get_db)):
    return crud.update_sql_script(db, script_id, script.model_dump())

@api_router.delete("/{script_id}")
def delete_script(script_id: int, db: PgConnection = Depends(get_db)):
    result = crud.delete_sql_script(db, script_id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail="SQL script not found")
    return {"message": "Script deleted successfully"}

@api_router.post("/execute")
def execute_script(request: schemas.SQLExecuteRequest, db: PgConnection = Depends(get_db)):
    try:
        return crud.execute_query(request.script_content, db)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))