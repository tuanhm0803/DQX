"""
Routes for reference tables functionality (rule_ref and source_ref tables)
"""
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Optional, Dict, Any

from app.database import get_db
from ..dependencies import templates, render_template

# Constants for queries
RULE_QUERY = """SELECT rule_id, rule_name, rule_desc FROM dq.rule_ref ORDER BY rule_id"""
SOURCE_QUERY = """SELECT source_id, source_name, source_desc FROM dq.source_ref ORDER BY source_id"""
TEMPLATE_NAME = "reference_tables.html"

# Add delete queries
DELETE_RULE_QUERY = """DELETE FROM dq.rule_ref WHERE rule_id = %s"""
DELETE_SOURCE_QUERY = """DELETE FROM dq.source_ref WHERE source_id = %s"""

# Create router - make sure it's at the module level so it can be imported
router = APIRouter(
    prefix="/references",
    tags=["references"],
)

@router.get("/", response_class=HTMLResponse)
def view_references(
    request: Request,
    db = Depends(get_db),
):
    """View and manage reference tables (rule_ref and source_ref)"""
    
    # Get all records from rule_ref
    try:
        cursor = db.cursor()
        cursor.execute(RULE_QUERY)
        rules = cursor.fetchall()
        # Convert tuple results to dicts for easier templating
        rule_column_names = [desc[0] for desc in cursor.description]
        rules = [dict(zip(rule_column_names, row)) for row in rules]
    except Exception as e:
        rules = []
        rule_error = str(e)
    
    # Get all records from source_ref
    try:
        cursor = db.cursor()
        cursor.execute(SOURCE_QUERY)
        sources = cursor.fetchall()
        # Convert tuple results to dicts for easier templating
        source_column_names = [desc[0] for desc in cursor.description]
        sources = [dict(zip(source_column_names, row)) for row in sources]
    except Exception as e:
        sources = []
        source_error = str(e)
    
    return render_template(
        TEMPLATE_NAME,
        {
            "request": request,
            "rules": rules,
            "sources": sources,
            "rule_error": rule_error if 'rule_error' in locals() else None,
            "source_error": source_error if 'source_error' in locals() else None
        }
    )

@router.post("/rule", response_class=HTMLResponse)
def add_rule(
    request: Request,
    rule_id: str = Form(...),
    rule_name: str = Form(...),
    rule_desc: str = Form(...),
    db = Depends(get_db),
):
    """Add a new rule to the rule_ref table"""
    try:
        cursor = db.cursor()
        insert_query = """
        INSERT INTO dq.rule_ref (rule_id, rule_name, rule_desc)
        VALUES (%s, %s, %s)
        """
        cursor.execute(insert_query, (rule_id, rule_name, rule_desc))
        db.commit()
        return RedirectResponse(url="/references/", status_code=303)
    except Exception as e:
        db.rollback()
        error_message = str(e)
        
        # Get all records from rule_ref and source_ref for re-rendering the page
        cursor = db.cursor()
        cursor.execute(RULE_QUERY)
        rules = cursor.fetchall()
        rule_column_names = [desc[0] for desc in cursor.description]
        rules = [dict(zip(rule_column_names, row)) for row in rules]
        
        cursor.execute(SOURCE_QUERY)
        sources = cursor.fetchall()
        source_column_names = [desc[0] for desc in cursor.description]
        sources = [dict(zip(source_column_names, row)) for row in sources]
        
        return render_template(
            TEMPLATE_NAME,
            {
                "request": request,
                "rules": rules,
                "sources": sources,
                "rule_error": error_message,
                "source_error": None,
                "rule_form_data": {
                    "rule_id": rule_id,
                    "rule_name": rule_name,
                    "rule_desc": rule_desc
                }
            }
        )

@router.post("/source", response_class=HTMLResponse)
def add_source(
    request: Request,
    source_id: str = Form(...),
    source_name: str = Form(...),
    source_desc: str = Form(...),
    db = Depends(get_db),
):
    """Add a new source to the source_ref table"""
    try:
        cursor = db.cursor()
        insert_query = """
        INSERT INTO dq.source_ref (source_id, source_name, source_desc)
        VALUES (%s, %s, %s)
        """
        cursor.execute(insert_query, (source_id, source_name, source_desc))
        db.commit()
        return RedirectResponse(url="/references/", status_code=303)
    except Exception as e:
        db.rollback()
        error_message = str(e)
        
        # Get all records from rule_ref and source_ref for re-rendering the page
        cursor = db.cursor()
        cursor.execute(RULE_QUERY)
        rules = cursor.fetchall()
        rule_column_names = [desc[0] for desc in cursor.description]
        rules = [dict(zip(rule_column_names, row)) for row in rules]
        
        cursor.execute(SOURCE_QUERY)
        sources = cursor.fetchall()
        source_column_names = [desc[0] for desc in cursor.description]
        sources = [dict(zip(source_column_names, row)) for row in sources]
        
        return render_template(
            TEMPLATE_NAME,
            {
                "request": request,
                "rules": rules,
                "sources": sources,
                "rule_error": None,
                "source_error": error_message,
                "source_form_data": {
                    "source_id": source_id,
                    "source_name": source_name,
                    "source_desc": source_desc
                }
            }
        )

@router.get("/rule/delete/{rule_id}", response_class=HTMLResponse)
def delete_rule(
    request: Request,
    rule_id: str,
    db = Depends(get_db),
):
    """Delete a rule from the rule_ref table"""
    try:
        cursor = db.cursor()
        # Execute delete query
        cursor.execute(DELETE_RULE_QUERY, (rule_id,))
        db.commit()
        return RedirectResponse(url="/references/", status_code=303)
    except Exception as e:
        db.rollback()
        # Log the error
        print(f"Error deleting rule {rule_id}: {e}")
        
        # Get all records from rule_ref and source_ref for re-rendering the page
        cursor = db.cursor()
        cursor.execute(RULE_QUERY)
        rules = cursor.fetchall()
        rule_column_names = [desc[0] for desc in cursor.description]
        rules = [dict(zip(rule_column_names, row)) for row in rules]
        
        cursor.execute(SOURCE_QUERY)
        sources = cursor.fetchall()
        source_column_names = [desc[0] for desc in cursor.description]
        sources = [dict(zip(source_column_names, row)) for row in sources]
        
        return render_template(
            TEMPLATE_NAME,
            {
                "request": request,
                "rules": rules,
                "sources": sources,
                "rule_error": f"Failed to delete rule {rule_id}: {str(e)}",
                "source_error": None
            }
        )

@router.get("/source/delete/{source_id}", response_class=HTMLResponse)
def delete_source(
    request: Request,
    source_id: str,
    db = Depends(get_db),
):
    """Delete a source from the source_ref table"""
    try:
        cursor = db.cursor()
        # Execute delete query
        cursor.execute(DELETE_SOURCE_QUERY, (source_id,))
        db.commit()
        return RedirectResponse(url="/references/", status_code=303)
    except Exception as e:
        db.rollback()
        # Log the error
        print(f"Error deleting source {source_id}: {e}")
        
        # Get all records from rule_ref and source_ref for re-rendering the page
        cursor = db.cursor()
        cursor.execute(RULE_QUERY)
        rules = cursor.fetchall()
        rule_column_names = [desc[0] for desc in cursor.description]
        rules = [dict(zip(rule_column_names, row)) for row in rules]
        
        cursor.execute(SOURCE_QUERY)
        sources = cursor.fetchall()
        source_column_names = [desc[0] for desc in cursor.description]
        sources = [dict(zip(source_column_names, row)) for row in sources]
        
        return render_template(
            TEMPLATE_NAME,
            {
                "request": request,
                "rules": rules,
                "sources": sources, 
                "rule_error": None,
                "source_error": f"Failed to delete source {source_id}: {str(e)}"
            }
        )
