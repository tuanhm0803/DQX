from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
import os
from app import crud
from app.database import get_db
from .routes import sql_scripts, stats, scheduler, bad_detail, auth, reference_tables, source_data_management, admin, user_actions_log
from .dependencies import templates, render_template
from .dependencies_auth import login_required, get_current_user_from_cookie
from .middleware_logging import UserActionLoggingMiddleware, UserMiddleware

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

# Add middlewares
app.add_middleware(UserMiddleware)  # Add this first to have user in all requests
app.add_middleware(UserActionLoggingMiddleware)  # Add logging middleware

# Session middleware (with 1 hour timeout - 3600 seconds)
app.add_middleware(
    SessionMiddleware,
    secret_key="DQX_SECRET_KEY",
    max_age=3600,  # 1 hour in seconds
    session_cookie="session"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include public authentication routes first (login, register, logout)
# These routes specifically don't have the login_required dependency
app.include_router(auth.public_router)

# Include protected authentication routes (profile)
app.include_router(auth.protected_router, dependencies=[Depends(login_required)])

# Include API routers
app.include_router(sql_scripts.api_router, prefix="/api/scripts", tags=["API - SQL Scripts"], dependencies=[Depends(login_required)])
app.include_router(stats.router, prefix="/api/stats", tags=["API - Stats"], dependencies=[Depends(login_required)])
app.include_router(scheduler.router, prefix="/api/schedules", tags=["API - Schedules"], dependencies=[Depends(login_required)])

# Include Page routers (protected by login_required)
app.include_router(sql_scripts.page_router, tags=["Pages"], dependencies=[Depends(login_required)])
app.include_router(scheduler.router, tags=["Pages"], dependencies=[Depends(login_required)])
app.include_router(bad_detail.router, dependencies=[Depends(login_required)])  # Add the bad_detail router
app.include_router(stats.page_router, tags=["Pages"], dependencies=[Depends(login_required)])  # Add the stats/visualization router
app.include_router(reference_tables.router, dependencies=[Depends(login_required)])  # Add the reference tables router
app.include_router(source_data_management.router, dependencies=[Depends(login_required)])  # Add the source data management router
app.include_router(admin.router, dependencies=[Depends(login_required)])  # Add the admin router
app.include_router(user_actions_log.router, dependencies=[Depends(login_required)])  # Add the user actions log router


# Mount static files directory
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

# Route to handle Chrome DevTools requests to avoid 404 errors in logs
@app.get("/.well-known/appspecific/com.chrome.devtools.json")
async def chrome_devtools_config():
    """
    Handle requests from Chrome DevTools to avoid 404 errors in logs.
    Returns an empty JSON object.
    """
    return {}

# Auth check middleware for all routes except root ("/")
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    # Skip auth check for root, login, logout, register, token, and static files
    path = request.url.path
    if (path == "/" or 
        path.startswith("/login") or 
        path.startswith("/logout") or 
        path.startswith("/register") or 
        path.startswith("/token") or 
        path.startswith("/static") or
        path.startswith("/api/auth/session-check")):
        return await call_next(request)
    
    # For all other routes, verify the user is logged in
    user = None
    try:
        # Check for user in request state (set by UserMiddleware)
        if hasattr(request.state, "user"):
            user = request.state.user
    except Exception:
        pass
        
    # If no user is found, and it's an API call, return 401
    if user is None and path.startswith("/api/"):
        return JSONResponse(
            status_code=401,
            content={"detail": "Authentication required"}
        )
    
    # Otherwise, continue to the next middleware or handler
    return await call_next(request)

# Page Endpoints
@app.get("/", response_class=HTMLResponse)
async def read_root(
    request: Request,
    db = Depends(get_db)
):
    """
    Main page - accessible without authentication.
    All other pages require login with a 1-hour session timeout.
    """
    script_count = crud.get_script_count(db)
    bad_detail_count = crud.get_bad_detail_count(db)
    stats_data = {"script_count": script_count, "bad_detail_count": bad_detail_count}
    return render_template("index.html", {"request": request, "stats": stats_data})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)