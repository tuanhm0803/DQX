from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from app.database import get_db
from app import crud
from app.dependencies import templates, render_template
from datetime import datetime, timedelta

# API router
router = APIRouter()

# Page router
page_router = APIRouter(tags=["Pages"])

@router.get("/")
def get_stats(db = Depends(get_db)):
    script_count = crud.get_script_count(db)
    bad_detail_count = crud.get_bad_detail_count(db)
    return {"script_count": script_count, "bad_detail_count": bad_detail_count}

@page_router.get("/visualization", response_class=HTMLResponse)
async def visualization_page(request: Request, rule_id: str = None, source_id: str = None, show_all: bool = False, db = Depends(get_db)):
    """
    Display the data visualization page with charts showing bad details over time.
    
    Args:
        request: The FastAPI request object
        rule_id: Optional filter for rule_id
        source_id: Optional filter for source_id
        show_all: Option to show all data (limited to 1000 records)
        db: Database connection
        
    Returns:
        HTML response with the visualization page
    """
    # Get available rule_ids and names for dropdown
    rule_ids = []
    try:
        rule_id_query = "SELECT rule_id, rule_name FROM dq.rule_ref ORDER BY rule_id"
        rule_id_results = crud.execute_query(rule_id_query, db)
        if rule_id_results and rule_id_results.get('data'):
            # Create tuples with (id, label) format
            rule_ids = [(row.get('rule_id'), f"{row.get('rule_id')} - {row.get('rule_name')}") 
                      for row in rule_id_results['data'] if row.get('rule_id')]
    except Exception as e:
        print(f"Error fetching rule_ids: {str(e)}")
    
    # Get available source_ids and names for dropdown
    source_ids = []
    try:
        source_id_query = "SELECT source_id, source_name FROM dq.source_ref ORDER BY source_id"
        source_id_results = crud.execute_query(source_id_query, db)
        if source_id_results and source_id_results.get('data'):
            # Create tuples with (id, label) format
            source_ids = [(row.get('source_id'), f"{row.get('source_id')} - {row.get('source_name')}") 
                        for row in source_id_results['data'] if row.get('source_id')]
    except Exception as e:
        print(f"Error fetching source_ids: {str(e)}")
    
    # Initialize variables for chart data
    chart_data = {}
    count_by_date = []
    count_by_rule = []
    count_by_source = []
    
    # Build the query based on filters
    limit = 1000 if show_all else 100
    query_str = """
        SELECT 
            DATE(txn_date) as date,
            rule_id,
            source_id,
            COUNT(*) as count
        FROM dq.bad_detail
    """
    
    conditions = []
    params = []
    if rule_id:
        conditions.append("rule_id = %s")
        params.append(rule_id)
    if source_id:
        conditions.append("source_id = %s")
        params.append(source_id)
    
    if conditions:
        query_str += " WHERE " + " AND ".join(conditions)
    
    # Add grouping and ordering
    query_str += """
        GROUP BY DATE(txn_date), rule_id, source_id
        ORDER BY date DESC, rule_id, source_id
        LIMIT %s
    """
    params.append(limit)
    
    # Execute query
    try:
        results = crud.execute_query(query_str, db, params)
        if results and results.get('data'):
            # Process data for charts
            
            # Create a dictionary to hold counts by date
            dates_dict = {}
            rules_dict = {}
            sources_dict = {}
            
            for row in results['data']:
                date_str = str(row['date'])
                rule = row['rule_id']
                source = row['source_id']
                count = row['count']
                
                # Count by date
                if date_str in dates_dict:
                    dates_dict[date_str] += count
                else:
                    dates_dict[date_str] = count
                
                # Count by rule
                if rule in rules_dict:
                    rules_dict[rule] += count
                else:
                    rules_dict[rule] = count
                
                # Count by source
                if source in sources_dict:
                    sources_dict[source] += count
                else:
                    sources_dict[source] = count
            
            # Sort by date and convert to list for the chart
            count_by_date = [{"date": k, "count": v} for k, v in sorted(dates_dict.items())]
            count_by_rule = [{"rule": k, "count": v} for k, v in sorted(rules_dict.items(), key=lambda x: x[1], reverse=True)]
            count_by_source = [{"source": k, "count": v} for k, v in sorted(sources_dict.items(), key=lambda x: x[1], reverse=True)]
            
            # Package all chart data
            chart_data = {
                "countByDate": count_by_date,
                "countByRule": count_by_rule,
                "countBySource": count_by_source
            }
    except Exception as e:
        print(f"Error executing query: {str(e)}")
    
    return render_template("visualization.html", {
        "request": request, 
        "rule_ids": rule_ids,
        "source_ids": source_ids,
        "rule_id": rule_id,
        "source_id": source_id,
        "show_all": show_all,
        "chart_data": chart_data
    })
