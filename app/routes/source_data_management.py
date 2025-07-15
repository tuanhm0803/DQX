"""
Routes for source data management functionality with multi-database support
"""
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from typing import Optional, List, Dict, Any
from app import crud
from app.database import get_db
from app.multi_db_manager import db_manager, get_db_connection
from psycopg2 import sql, Error as PsycopgError
from app.dependencies import templates, render_template
from app.role_permissions import can_admin_creator_access

# Router for HTML pages
router = APIRouter(tags=["Pages"])

@router.get("/source_data_management", response_class=HTMLResponse)
async def source_data_management_page(
    request: Request, 
    db = Depends(get_db),
    user = Depends(can_admin_creator_access)
):
    """
    Display the source data management page where users can create tables in the target database
    and query data from source databases.
    
    Args:
        request: The FastAPI request object
        db: Database connection (for authentication/session)
        
    Returns:
        HTML response with the source data management page
    """
    # Get target database connection info
    target_connection = db_manager.get_target_connection_info()
    
    # Get all source database connections
    source_connections = db_manager.get_source_connections()
    
    # Get all available database connections for data querying
    all_connections = db_manager.get_all_connections()
    
    # Get target database info with schemas and tables
    target_data = None
    if target_connection:
        try:
            target_id = target_connection['id']
            schemas = db_manager.get_schemas(target_id)
            stg_tables = db_manager.get_tables(target_id, 'stg') if 'stg' in schemas else []
            
            target_data = {
                'connection': target_connection,
                'schemas': schemas,
                'stg_tables': stg_tables,
                'has_stg_schema': 'stg' in schemas
            }
        except Exception as e:
            print(f"Error fetching target database data: {str(e)}")
            target_data = {
                'connection': target_connection,
                'schemas': [],
                'stg_tables': [],
                'has_stg_schema': False,
                'error': str(e)
            }
    
    # Get source database info
    source_data = []
    for conn in source_connections:
        try:
            schemas = db_manager.get_schemas(conn['id'])
            source_data.append({
                'connection': conn,
                'schemas': schemas,
                'error': None
            })
        except Exception as e:
            print(f"Error fetching data for source connection {conn['id']}: {str(e)}")
            source_data.append({
                'connection': conn,
                'schemas': [],
                'error': str(e)
            })
    
    return render_template("source_data_management.html", {
        "request": request,
        "target_data": target_data,
        "source_data": source_data,
        "all_connections": all_connections,
    })

@router.post("/source_data_management/create_table")
async def create_table(
    request: Request,
    user = Depends(can_admin_creator_access),
    table_name: str = Form(...),
    sql_script: str = Form(...),
    source_connections: str = Form(None)  # JSON string of selected source connections
):
    """
    Create a new table in the target database's stg schema using data from source databases.
    
    Args:
        request: The FastAPI request object
        table_name: Name of the table to create
        sql_script: SQL script to create the table (can reference source databases)
        source_connections: JSON string of source connections to make available
        
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
        
        # Get the target database connection
        target_conn = db_manager.get_target_connection()
        if not target_conn:
            return JSONResponse(
                status_code=500,
                content={"success": False, "message": "Target database connection not available"}
            )
        
        try:
            cursor = target_conn.cursor()
            
            # Ensure the stg schema exists
            cursor.execute("CREATE SCHEMA IF NOT EXISTS stg")
            
            # Create the table in the target database
            # The SQL script should be a SELECT statement that can reference source databases
            create_query = f"CREATE TABLE IF NOT EXISTS stg.{table_name} AS {sql_script}"
            cursor.execute(create_query)
            
            target_conn.commit()
            cursor.close()
            target_conn.close()
            
            target_info = db_manager.get_target_connection_info()
            target_name = target_info['name'] if target_info else 'target database'
            
            return JSONResponse(
                content={"success": True, "message": f"Table stg.{table_name} created successfully in {target_name}."}
            )
            
        except Exception as e:
            target_conn.rollback()
            target_conn.close()
            return JSONResponse(
                status_code=500,
                content={"success": False, "message": f"Error creating table: {str(e)}"}
            )
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"Error: {str(e)}"}
        )

@router.post("/source_data_management/insert_data")
async def insert_data(
    request: Request,
    user = Depends(can_admin_creator_access),
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
    table_name: str = Form(...),
    user = Depends(can_admin_creator_access)
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
    table_name: str = Form(...),
    user = Depends(can_admin_creator_access)
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
    db = Depends(get_db),
    user = Depends(can_admin_creator_access)
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

# API endpoints for multi-database management

@router.get("/api/database_connections")
async def get_database_connections(request: Request, user = Depends(can_admin_creator_access)):
    """Get all available database connections"""
    try:
        connections = db_manager.get_all_connections()
        return JSONResponse(content={"success": True, "connections": connections})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"Error fetching connections: {str(e)}"}
        )

@router.get("/api/database_connections/{connection_id}/schemas")
async def get_connection_schemas(connection_id: str, request: Request, user = Depends(can_admin_creator_access)):
    """Get all schemas for a specific database connection"""
    try:
        schemas = db_manager.get_schemas(connection_id)
        return JSONResponse(content={"success": True, "schemas": schemas})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"Error fetching schemas: {str(e)}"}
        )

@router.get("/api/database_connections/{connection_id}/schemas/{schema_name}/tables")
async def get_schema_tables(connection_id: str, schema_name: str, request: Request, user = Depends(can_admin_creator_access)):
    """Get all tables for a specific schema in a database connection"""
    try:
        tables = db_manager.get_tables(connection_id, schema_name)
        return JSONResponse(content={"success": True, "tables": tables})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"Error fetching tables: {str(e)}"}
        )

@router.post("/api/database_connections/{connection_id}/test")
async def test_database_connection(connection_id: str, request: Request, user = Depends(can_admin_creator_access)):
    """Test a specific database connection"""
    try:
        result = db_manager.test_connection(connection_id)
        status_code = 200 if result["success"] else 400
        return JSONResponse(content=result, status_code=status_code)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"Error testing connection: {str(e)}"}
        )
