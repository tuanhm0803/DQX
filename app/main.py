from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
import os
from app import crud
from app.database import get_db
from psycopg2.extensions import connection as PgConnection
from .routes import tables, query, sql_scripts, stats, scheduler, bad_detail, chat_logger
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
app.include_router(chat_logger.router)  # Contains both API and page routes

# Include Page routers
app.include_router(sql_scripts.page_router, tags=["Pages"])
app.include_router(scheduler.router, tags=["Pages"])
app.include_router(bad_detail.router)  # Add the bad_detail router
app.include_router(stats.page_router, tags=["Pages"])  # Add the stats/visualization router


# Mount static files directory
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

# Page Endpoints
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, db: PgConnection = Depends(get_db)):
    script_count = crud.get_script_count(db)
    bad_detail_count = crud.get_bad_detail_count(db)
    stats_data = {"script_count": script_count, "bad_detail_count": bad_detail_count}
    return templates.TemplateResponse("index.html", {"request": request, "stats": stats_data})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)