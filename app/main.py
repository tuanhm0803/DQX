from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
import os
from app import crud
from app.database import get_db
from psycopg2.extensions import connection as PgConnection
from .routes import tables, query, sql_scripts, stats, scheduler
from .dependencies import templates

# FastAPI app
app = FastAPI(title="Database Explorer API")

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # In a production environment, you might want to log the exception
    print(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"An internal server error occurred: {str(exc)}"},
    )

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(tables.router, prefix="/api/tables", tags=["API - Tables"])
app.include_router(query.router, prefix="/api/query_db", tags=["API - Query"])
app.include_router(sql_scripts.api_router, prefix="/api/scripts", tags=["API - SQL Scripts"])
app.include_router(stats.router, prefix="/api/stats", tags=["API - Stats"])
app.include_router(scheduler.router, prefix="/api/schedules", tags=["API - Schedules"])

# Include Page routers
app.include_router(sql_scripts.page_router, tags=["Pages"])
app.include_router(scheduler.router, tags=["Pages"])


# Mount static files directory
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

# Page Endpoints
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, db: PgConnection = Depends(get_db)):
    stats_data = crud.get_stats(db)
    return templates.TemplateResponse("index.html", {"request": request, "stats": stats_data})

@app.get("/bad_detail_query", response_class=HTMLResponse)
async def bad_detail_query_page(request: Request, rule_id: str = None, source_id: str = None, db: PgConnection = Depends(get_db)):
    headers = []
    data = []
    if rule_id or source_id:
        query_str = "SELECT * FROM dq.bad_detail"
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
        query_str += " LIMIT 100;"

        results = crud.execute_query(db, query_str, params)
        if results and results['data']:
            headers = results['data'][0].keys()
            data = [row.values() for row in results['data']]

    return templates.TemplateResponse("bad_detail_query.html", {"request": request, "headers": headers, "data": data, "rule_id": rule_id, "source_id": source_id})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)