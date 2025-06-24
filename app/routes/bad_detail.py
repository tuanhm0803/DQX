"""
Routes for bad detail query functionality
"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from app import crud
from app.database import get_db
from psycopg2.extensions import connection as PgConnection
from app.dependencies import templates

# Router for HTML pages
router = APIRouter(tags=["Pages"])

@router.get("/bad_detail_query", response_class=HTMLResponse)
async def bad_detail_query_page(request: Request, rule_id: str = None, source_id: str = None, db: PgConnection = Depends(get_db)):
    """
    Display the bad detail query page with optional filtering by rule_id and source_id.
    
    Args:
        request: The FastAPI request object
        rule_id: Optional filter for rule_id
        source_id: Optional filter for source_id
        db: Database connection
        
    Returns:
        HTML response with the bad detail query page
    """
    headers = []
    data = []
    
    # Get available rule_ids for dropdown
    rule_ids = []
    try:
        rule_id_query = "SELECT DISTINCT rule_id FROM dq.bad_detail ORDER BY rule_id"
        rule_id_results = crud.execute_query(rule_id_query, db)
        if rule_id_results and rule_id_results.get('data'):
            rule_ids = [row.get('rule_id') for row in rule_id_results['data'] if row.get('rule_id')]
    except Exception as e:
        print(f"Error fetching rule_ids: {str(e)}")
    
    # Get available source_ids for dropdown
    source_ids = []
    try:
        source_id_query = "SELECT DISTINCT source_id FROM dq.bad_detail ORDER BY source_id"
        source_id_results = crud.execute_query(source_id_query, db)
        if source_id_results and source_id_results.get('data'):
            source_ids = [row.get('source_id') for row in source_id_results['data'] if row.get('source_id')]
    except Exception as e:
        print(f"Error fetching source_ids: {str(e)}")
      # Execute the main query if filters are provided
    if rule_id or source_id:
        query_str = "SELECT * FROM dq.bad_detail"
        conditions = []
        params = []
        if rule_id and rule_id != "All":
            conditions.append("rule_id = %s")
            params.append(rule_id)
        if source_id and source_id != "All":
            conditions.append("source_id = %s")
            params.append(source_id)
        
        if conditions:
            query_str += " WHERE " + " AND ".join(conditions)
        query_str += " LIMIT 1000;"
        results = crud.execute_query(query_str, db, params)
        if results and results.get('data'):
            headers = results['data'][0].keys()
            data = [row.values() for row in results['data']]

    return templates.TemplateResponse("bad_detail_query.html", {
        "request": request, 
        "headers": headers, 
        "data": data, 
        "rule_id": rule_id, 
        "source_id": source_id,
        "rule_ids": rule_ids,
        "source_ids": source_ids
    })
