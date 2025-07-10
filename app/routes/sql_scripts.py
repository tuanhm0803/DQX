from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import List, Optional
from app import crud, schemas
from app.database import get_db
from app.dependencies import templates, render_template

# Router for API endpoints
api_router = APIRouter()

# Router for HTML pages
page_router = APIRouter()

# Constants
SQL_EDITOR_TEMPLATE = "sql_editor.html"

# --- Page Endpoints ---

@page_router.get("/editor", response_class=HTMLResponse)
async def sql_editor_page(request: Request, script_id: Optional[int] = None, db = Depends(get_db)):
    # Fix for the decode attribute error by properly checking and converting script_id
    if script_id is not None:
        if isinstance(script_id, bytes):
            script_id = script_id.decode('utf-8')
        try:
            script_id = int(script_id)
        except (ValueError, TypeError):
            script_id = None
            
    scripts = crud.get_sql_scripts(db)
    selected_script = None
    if script_id:
        selected_script = crud.get_sql_script(db, script_id)
    return render_template(SQL_EDITOR_TEMPLATE, {
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
    db = Depends(get_db)
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
    db = Depends(get_db)
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
    return render_template(SQL_EDITOR_TEMPLATE, {
        "request": request, 
        "scripts": scripts, 
        "selected_script": {"content": content}, # Pass back the executed script
        "results": results,
        "error": error
    })

@page_router.get("/editor/delete/{script_id}")
async def delete_script_form(script_id: int, db = Depends(get_db)):
    crud.delete_sql_script(db, script_id)
    return RedirectResponse(url="/editor", status_code=303)

# Add populate and publish page routes
@page_router.get("/editor/{script_id}/populate")
async def populate_table_form(request: Request, script_id: int, db = Depends(get_db)):
    try:
        # Get script name for better messaging
        selected_script = crud.get_sql_script(db, script_id)
        script_name = selected_script.get("name", f"Script #{script_id}")
        
        # Execute the populate function
        result = crud.populate_script_result_table(db, script_id)
        
        # Get all scripts for page rendering
        scripts = crud.get_sql_scripts(db)
        
        # Success message with row count if available
        success_message = f"Successfully populated staging table with data from '{script_name}'."
        if result and "rows_affected" in result:
            success_message += f" {result['rows_affected']} rows processed."
        
        return render_template(SQL_EDITOR_TEMPLATE, {
            "request": request, 
            "scripts": scripts, 
            "selected_script": selected_script,
            "results": None,
            "success": success_message
        })
    except Exception as e:
        # Get all scripts for error page rendering
        scripts = crud.get_sql_scripts(db)
        selected_script = crud.get_sql_script(db, script_id)
        return render_template(SQL_EDITOR_TEMPLATE, {
            "request": request, 
            "scripts": scripts, 
            "selected_script": selected_script,
            "results": None,
            "error": f"Failed to populate table: {str(e)}"
        })

@page_router.get("/editor/{script_id}/publish")
async def publish_results_form(request: Request, script_id: int, db = Depends(get_db)):
    try:
        # Get script name for better messaging
        selected_script = crud.get_sql_script(db, script_id)
        script_name = selected_script.get("name", f"Script #{script_id}")
        
        # Execute the publish function
        result = crud.publish_script_results(db, script_id)
        
        # Get all scripts for page rendering
        scripts = crud.get_sql_scripts(db)
        
        # Success message with row count if available
        success_message = f"Successfully published results from '{script_name}' to production table."
        if result and "rows_affected" in result:
            success_message += f" {result['rows_affected']} rows moved to production."
        
        return render_template(SQL_EDITOR_TEMPLATE, {
            "request": request, 
            "scripts": scripts, 
            "selected_script": selected_script,
            "results": None,
            "success": success_message
        })
    except Exception as e:
        # Get all scripts for error page rendering
        scripts = crud.get_sql_scripts(db)
        selected_script = crud.get_sql_script(db, script_id)
        return render_template(SQL_EDITOR_TEMPLATE, {
            "request": request, 
            "scripts": scripts, 
            "selected_script": selected_script,
            "results": None,
            "error": f"Failed to publish results: {str(e)}"
        })

# --- API Endpoints ---

@api_router.get("/", response_model=List[schemas.SQLScript])
def get_scripts(db = Depends(get_db)):
    return crud.get_sql_scripts(db)

@api_router.get("/{script_id}", response_model=schemas.SQLScript)
def get_script(script_id: int, db = Depends(get_db)):
    script = crud.get_sql_script(db, script_id)
    if script is None:
        raise HTTPException(status_code=404, detail="SQL script not found")
    return script

@api_router.post("/", response_model=schemas.SQLScript)
def create_script(script: schemas.SQLScriptCreate, db = Depends(get_db)):
    return crud.create_sql_script(db, script.model_dump())

@api_router.put("/{script_id}", response_model=schemas.SQLScript)
def update_script(script_id: int, script: schemas.SQLScriptCreate, db = Depends(get_db)):
    return crud.update_sql_script(db, script_id, script.model_dump())

@api_router.delete("/{script_id}")
def delete_script(script_id: int, db = Depends(get_db)):
    result = crud.delete_sql_script(db, script_id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail="SQL script not found")
    return {"message": "Script deleted successfully"}

@api_router.post("/execute")
def execute_script(request: schemas.SQLExecuteRequest, db = Depends(get_db)):
    try:
        return crud.execute_query(request.script_content, db)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Add populate and publish endpoints
@api_router.post("/{script_id}/populate_table")
def populate_table(script_id: int, db = Depends(get_db)):
    """Populate the staging table for a specific SQL script"""
    try:
        result = crud.populate_script_result_table(db, script_id)
        return result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=f"Failed to populate table for script {script_id}: {str(ve)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@api_router.post("/{script_id}/publish")
def publish_results(script_id: int, db = Depends(get_db)):
    """Publish results from the script's staging table to the main bad_detail table."""
    try:
        result = crud.publish_script_results(db, script_id)
        return result
    except Exception as e:
        if isinstance(e, ValueError):
            raise HTTPException(status_code=400, detail=f"Failed to publish results for script {script_id}: {str(e)}")
        else:
            raise HTTPException(status_code=500, detail=f"An unexpected server error occurred while publishing results for script {script_id}: {str(e)}")