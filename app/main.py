from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import os
from app import crud
from app.database import get_db
from psycopg2.extensions import connection as PgConnection
from .routes import tables, query, sql_scripts, stats, scheduler, bad_detail, auth, reference_tables, source_data_management, admin
from .dependencies import templates, render_template
from .dependencies_auth import login_required, get_current_user_from_cookie

# User middleware
class UserMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Store user in request state if available
        conn = None
        try:
            conn = next(get_db())
            # Extract token from cookies if available
            cookies = request.cookies
            access_token = cookies.get("access_token")
            
            # Only process if there's a token
            if access_token:
                # Extract the token from the "Bearer <token>" format
                if access_token.startswith("Bearer "):
                    token = access_token[7:]
                else:
                    token = access_token
                    
                # Try to decode the token and get the user
                from jose import JWTError, jwt
                from app.auth import SECRET_KEY, ALGORITHM
                from app import crud
                
                try:
                    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                    username = payload.get("sub")
                    if username:
                        user = crud.get_user_by_username(conn, username)
                        request.state.user = user
                except JWTError:
                    request.state.user = None
            else:
                request.state.user = None
                
        except Exception as e:
            print(f"Error in user middleware: {e}")
            request.state.user = None
        finally:
            if conn:
                conn.close()
                
        response = await call_next(request)
        return response

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
app.include_router(tables.router, prefix="/api/tables", tags=["API - Tables"], dependencies=[Depends(login_required)])
app.include_router(query.router, prefix="/api/query_db", tags=["API - Query"], dependencies=[Depends(login_required)])
app.include_router(sql_scripts.api_router, prefix="/api/scripts", tags=["API - SQL Scripts"], dependencies=[Depends(login_required)])
app.include_router(stats.router, prefix="/api/stats", tags=["API - Stats"], dependencies=[Depends(login_required)])
app.include_router(scheduler.router, prefix="/api/schedules", tags=["API - Schedules"], dependencies=[Depends(login_required)])
# Chat logger functionality has been removed
from app.routes.test_route import test_router
app.include_router(test_router) # Test router for debugging

# Include Page routers (protected by login_required)
app.include_router(sql_scripts.page_router, tags=["Pages"], dependencies=[Depends(login_required)])
app.include_router(scheduler.router, tags=["Pages"], dependencies=[Depends(login_required)])
app.include_router(bad_detail.router, dependencies=[Depends(login_required)])  # Add the bad_detail router
app.include_router(stats.page_router, tags=["Pages"], dependencies=[Depends(login_required)])  # Add the stats/visualization router
app.include_router(reference_tables.router, dependencies=[Depends(login_required)])  # Add the reference tables router
app.include_router(source_data_management.router, dependencies=[Depends(login_required)])  # Add the source data management router
app.include_router(admin.router, dependencies=[Depends(login_required)])  # Add the admin router


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

# Page Endpoints
@app.get("/", response_class=HTMLResponse)
async def read_root(
    request: Request, 
    user = Depends(login_required),
    db: PgConnection = Depends(get_db)
):
    script_count = crud.get_script_count(db)
    bad_detail_count = crud.get_bad_detail_count(db)
    stats_data = {"script_count": script_count, "bad_detail_count": bad_detail_count}
    return render_template("index.html", {"request": request, "stats": stats_data})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)