"""
Routes for bad detail query functionality
"""
from fastapi import APIRouter, Request, Depends, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Optional, List
from app import crud
from app.database import get_db
from app.dependencies import templates, render_template

# Router for HTML pages
router = APIRouter(tags=["Pages"])

def fetch_filter_options(db, filter_name, search_term=None):
    """Helper function to fetch filter options with optional search filtering"""
    options = []
    try:
        if filter_name == "rule_id":
            # Get rule_id and rule_name for filter options
            query = "SELECT rule_id, rule_name FROM dq.rule_ref ORDER BY rule_id"
            results = crud.execute_query(query, db)
            if results and results.get('data'):
                # Create options with ID and name
                options = [(row.get('rule_id'), f"{row.get('rule_id')} - {row.get('rule_name')}") 
                          for row in results['data'] if row.get('rule_id')]
        elif filter_name == "source_id":
            # Get source_id and source_name for filter options
            query = "SELECT source_id, source_name FROM dq.source_ref ORDER BY source_id"
            results = crud.execute_query(query, db)
            if results and results.get('data'):
                # Create options with ID and name
                options = [(row.get('source_id'), f"{row.get('source_id')} - {row.get('source_name')}") 
                          for row in results['data'] if row.get('source_id')]
        else:
            # For other filters, use the original approach
            query = f"SELECT DISTINCT {filter_name} FROM dq.bad_detail ORDER BY {filter_name}"
            results = crud.execute_query(query, db)
            if results and results.get('data'):
                options = [(row.get(filter_name), row.get(filter_name)) 
                          for row in results['data'] if row.get(filter_name)]
        
        # If search term is provided, filter options on the server side
        if search_term and options:
            search_term_lower = search_term.lower()
            options = [(id_val, label) for id_val, label in options 
                      if search_term_lower in str(label).lower()]
    except Exception as e:
        print(f"Error fetching {filter_name}: {str(e)}")
    return options

def execute_bad_detail_query(db, rule_id=None, source_id=None):
    """Helper function to execute the main query with filters"""
    headers = []
    data = []
    
    if rule_id or source_id:
        # Updated query to join with rule_ref and source_ref tables
        query_str = """
            SELECT c.source_name, b.rule_name, a.* 
            FROM dq.bad_detail a
            LEFT JOIN dq.rule_ref b ON a.rule_id = b.rule_id
            LEFT JOIN dq.source_ref c ON a.source_id = c.source_id
        """
        conditions = []
        params = []
        if rule_id and rule_id != "All":
            conditions.append("a.rule_id = %s")
            params.append(rule_id)
        if source_id and source_id != "All":
            conditions.append("a.source_id = %s")
            params.append(source_id)
        
        if conditions:
            query_str += " WHERE " + " AND ".join(conditions)
        query_str += " LIMIT 1000;"
        results = crud.execute_query(query_str, db, params)
        if results and results.get('data'):
            headers = results['data'][0].keys()
            data = [row.values() for row in results['data']]
            
    return headers, data

@router.get("/bad_detail_query", response_class=HTMLResponse)
async def bad_detail_query_page(
    request: Request, 
    rule_id: Optional[str] = None, 
    source_id: Optional[str] = None,
    search_term: Optional[str] = None,
    page: int = 1,
    db = Depends(get_db)
):
    """
    Display the bad detail query page with optional filtering by rule_id and source_id.
    
    Args:
        request: The FastAPI request object
        rule_id: Optional filter for rule_id
        source_id: Optional filter for source_id
        search_term: Optional search term to filter dropdown options
        page: Current page number for pagination
        db: Database connection
        
    Returns:
        HTML response with the bad detail query page
    """
    # Get filter options
    rule_ids = fetch_filter_options(db, "rule_id", search_term)
    source_ids = fetch_filter_options(db, "source_id", search_term)
    
    # Execute main query
    headers, data = execute_bad_detail_query(db, rule_id, source_id)

    # Add pagination if needed
    items_per_page = 20
    total_records = len(data) if data else 0
    total_pages = (total_records + items_per_page - 1) // items_per_page  # Ceiling division
    
    # Handle invalid page number
    if page < 1:
        page = 1
    elif page > total_pages and total_pages > 0:
        page = total_pages
    
    # Paginate data if needed
    paginated_data = []
    if data:
        start_idx = (page - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, total_records)
        paginated_data = data[start_idx:end_idx]
    else:
        paginated_data = data
    
    return render_template("bad_detail_query.html", {
        "request": request, 
        "headers": headers, 
        "data": paginated_data, 
        "rule_id": rule_id, 
        "source_id": source_id,
        "rule_ids": rule_ids,
        "source_ids": source_ids,
        "search_term": search_term,
        "page": page,
        "total_pages": total_pages,
        "total_records": total_records
    })

@router.get("/bad_detail_query/search", response_class=HTMLResponse)
async def search_options(
    request: Request,
    field: str,
    search_term: Optional[str] = None,
    db = Depends(get_db)
):
    """
    Search for rule_id or source_id options based on search term.
    This is a server-side alternative to client-side JavaScript filtering.
    
    Args:
        request: The FastAPI request object
        field: Field to search (rule_id or source_id)
        search_term: Term to search for
        db: Database connection
        
    Returns:
        HTML response with filtered options
    """
    # Validate field
    if field not in ["rule_id", "source_id"]:
        options = []
    else:
        # Reuse the helper function to fetch filtered options
        options = fetch_filter_options(db, field, search_term)
    
    # Return a simple HTML fragment with the filtered options
    return render_template(
        "partials/dropdown_options.html", 
        {"request": request, "options": options, "selected": None}
    )
