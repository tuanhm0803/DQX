"""
Routes for source data management functionality
"""
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from typing import Optional, List, Dict, Any
from app import crud
from app.database import get_db
from psycopg2 import sql, Error as PsycopgError
from app.dependencies import templates, render_template
from app.role_permissions import can_create_table, can_insert_data

# Router for HTML pages
router = APIRouter(tags=["Pages"])

@router.get("/source_data_management", response_class=HTMLResponse)
async def source_data_management_page(
    request: Request, 
    db = Depends(get_db)
):
    """
    Display the source data management page where users can create, manage,
    and interact with tables in the stg schema.
    
    Args:
        request: The FastAPI request object
        db: Database connection
        
    Returns:
        HTML response with the source data management page
    """
    # Get all tables in the stg schema
    stg_tables = []
    try:
        # Query to get all tables in the stg schema
        query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'stg'
            ORDER BY table_name
        """
        result = crud.execute_query(query, db)
        if result and result.get('data'):
            stg_tables = [row.get('table_name') for row in result['data']]
    except Exception as e:
        print(f"Error fetching stg tables: {str(e)}")
    
    return render_template("source_data_management.html", {
        "request": request,
        "stg_tables": stg_tables,
    })

@router.post("/source_data_management/create_table")
async def create_table(
    request: Request,
    user = Depends(can_create_table),
    db = Depends(get_db),
    table_name: str = Form(...),
    sql_script: str = Form(...)
):
    """
    Create a new table in the stg schema using a SQL script.
    
    Args:
        request: The FastAPI request object
        db: Database connection
        table_name: Name of the table to create
        sql_script: SQL script to create the table
        
    Returns:
        JSON response with success/error message
    """
    try:
        # Validate the table name
        if not table_name.isidentifier():
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Invalid table name. Use only letters, numbers, and underscores."}
            )
        
        # Create the table
        # We'll use CREATE TABLE IF NOT EXISTS to avoid errors if table already exists
        create_query = f"CREATE TABLE IF NOT EXISTS stg.{table_name} AS {sql_script}"
        
        # Execute the query
        cursor = db.cursor()
        cursor.execute(create_query)
        db.commit()
        cursor.close()
        
        return JSONResponse(
            content={"success": True, "message": f"Table stg.{table_name} created successfully."}
        )
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"Error creating table: {str(e)}"}
        )

@router.post("/source_data_management/insert_data")
async def insert_data(
    request: Request,
    user = Depends(can_insert_data),
    db = Depends(get_db),
    table_name: str = Form(...),
    insert_script: str = Form(...)
):
    """
    Insert data into a table in the stg schema using a SQL script.
    
    Args:
        request: The FastAPI request object
        db: Database connection
        table_name: Name of the table to insert data into
        insert_script: SQL script to insert data
        
    Returns:
        JSON response with success/error message
    """
    try:
        # Validate the table name
        if not table_name.isidentifier():
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Invalid table name. Use only letters, numbers, and underscores."}
            )
        
        # Check if table exists
        check_query = """
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.tables 
                WHERE table_schema = 'stg' AND table_name = %s
            )
        """
        cursor = db.cursor()
        cursor.execute(check_query, (table_name,))
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            cursor.close()
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": f"Table stg.{table_name} does not exist."}
            )
        
        # Execute the insert script
        cursor.execute(f"INSERT INTO stg.{table_name} {insert_script}")
        rows_affected = cursor.rowcount
        db.commit()
        cursor.close()
        
        return JSONResponse(
            content={
                "success": True, 
                "message": f"Data inserted successfully. {rows_affected} rows affected."
            }
        )
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"Error inserting data: {str(e)}"}
        )

@router.post("/source_data_management/truncate_table")
async def truncate_table(
    request: Request,
    db = Depends(get_db),
    table_name: str = Form(...)
):
    """
    Truncate a table in the stg schema.
    
    Args:
        request: The FastAPI request object
        db: Database connection
        table_name: Name of the table to truncate
        
    Returns:
        JSON response with success/error message
    """
    try:
        # Validate the table name
        if not table_name.isidentifier():
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Invalid table name. Use only letters, numbers, and underscores."}
            )
        
        # Truncate the table
        cursor = db.cursor()
        cursor.execute(f"TRUNCATE TABLE stg.{table_name}")
        db.commit()
        cursor.close()
        
        return JSONResponse(
            content={"success": True, "message": f"Table stg.{table_name} truncated successfully."}
        )
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"Error truncating table: {str(e)}"}
        )

@router.post("/source_data_management/drop_table")
async def drop_table(
    request: Request,
    db = Depends(get_db),
    table_name: str = Form(...)
):
    """
    Drop a table in the stg schema.
    
    Args:
        request: The FastAPI request object
        db: Database connection
        table_name: Name of the table to drop
        
    Returns:
        JSON response with success/error message
    """
    try:
        # Validate the table name
        if not table_name.isidentifier():
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Invalid table name. Use only letters, numbers, and underscores."}
            )
        
        # Drop the table
        cursor = db.cursor()
        cursor.execute(f"DROP TABLE IF EXISTS stg.{table_name}")
        db.commit()
        cursor.close()
        
        return JSONResponse(
            content={"success": True, "message": f"Table stg.{table_name} dropped successfully."}
        )
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"Error dropping table: {str(e)}"}
        )

@router.get("/source_data_management/view_data/{table_name}")
async def view_table_data(
    request: Request,
    table_name: str,
    db = Depends(get_db)
):
    """
    View data from a table in the stg schema.
    
    Args:
        request: The FastAPI request object
        table_name: Name of the table to view
        db: Database connection
        
    Returns:
        JSON response with table data and structure
    """
    try:
        # Validate the table name
        if not table_name.isidentifier():
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Invalid table name. Use only letters, numbers, and underscores."}
            )
        
        # Get table structure
        structure_query = f"""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'stg' AND table_name = '{table_name}'
            ORDER BY ordinal_position
        """
        
        # Get table data
        data_query = f"SELECT * FROM stg.{table_name} LIMIT 100"
        
        structure_result = crud.execute_query(structure_query, db)
        data_result = crud.execute_query(data_query, db)
        
        return JSONResponse(
            content={
                "success": True,
                "structure": structure_result.get('data', []),
                "data": data_result.get('data', []),
                "columns": [col.get('column_name') for col in structure_result.get('data', [])],
                "total_rows": len(data_result.get('data', [])),
                "table_name": table_name
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"Error retrieving table data: {str(e)}"}
        )
