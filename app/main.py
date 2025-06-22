from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse
import os
from .routes import tables, query, sql_scripts, stats, scheduler

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

# Include routes
app.include_router(tables.router, prefix="/tables", tags=["Tables"])
app.include_router(query.router, prefix="/query_db", tags=["Query"])
app.include_router(sql_scripts.router, prefix="/scripts", tags=["SQL Scripts"])
app.include_router(stats.router, prefix="/stats", tags=["Stats"])
app.include_router(scheduler.router, prefix="/schedules", tags=["Schedules"])

# Mount static files directory
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

# Redirect to SQL editor
@app.get("/editor", response_class=RedirectResponse)
def redirect_to_editor():
    return "/static/sql_editor.html"

@app.get("/scheduler", response_class=RedirectResponse)
def redirect_to_scheduler():
    return "/static/scheduler.html"

@app.get("/bad_detail_query", response_class=RedirectResponse)
def redirect_to_bad_detail_query():
    return "/static/bad_detail_query.html"

# Root endpoint
@app.get("/", response_class=RedirectResponse)
def read_root():
    return "/static/index.html"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)