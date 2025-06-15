from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from .routes import tables, query, sql_scripts

# FastAPI app
app = FastAPI(title="Database Explorer API")

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
app.include_router(query.router, prefix="/query", tags=["Query"])
app.include_router(sql_scripts.router, prefix="/scripts", tags=["SQL Scripts"])

# Mount static files directory
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

# Redirect to SQL editor
@app.get("/editor", response_class=RedirectResponse)
def redirect_to_editor():
    return "/static/sql_editor.html"

# Root endpoint
@app.get("/", response_class=RedirectResponse)
def read_root():
    return "/static/index.html"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)