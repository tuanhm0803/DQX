"""
Authentication routes for DQX
"""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, Form, status, Response, Cookie
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from typing import Optional
from jose import JWTError, jwt
from psycopg2.extensions import connection as PgConnection

from app import crud
from app.auth import authenticate_user, create_access_token, get_current_active_user
from app.database import get_db
from app.dependencies import templates, render_template
from app.models import User
from app.schemas import Token, UserCreate

# Constants
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # Changed from 30 to 60 minutes (1 hour)

# Routers - split into public (no auth) and protected (requires auth)
public_router = APIRouter(tags=["Authentication - Public"]) 
protected_router = APIRouter(tags=["Authentication - Protected"])

# API Routes
@public_router.post("/token", response_model=Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: PgConnection = Depends(get_db)
):
    """
    OAuth2 compatible token login, returns an access token.
    Used primarily for API authentication.
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

# Page Routes
@public_router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, next: str = "/"):
    """Render the login page."""
    return render_template(
        "login.html", 
        {"request": request, "next": next}
    )

@public_router.post("/login", response_class=HTMLResponse)
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form("/"),
    db: PgConnection = Depends(get_db)
):
    """Process login form submission."""
    user = authenticate_user(db, username, password)
    if not user:
        return render_template(
            "login.html", 
            {
                "request": request, 
                "error": "Invalid username or password",
                "next": next
            },
            status_code=400
        )
    
    # Create access token
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    # Create response with cookie
    response = RedirectResponse(url=next, status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax"
    )
    
    return response

@public_router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    """Registration is disabled. Redirect to login page."""
    return RedirectResponse(
        url="/login", 
        status_code=status.HTTP_302_FOUND
    )

@public_router.post("/register", response_class=HTMLResponse)
def register(request: Request):
    """Registration is disabled. Redirect to login page."""
    return RedirectResponse(
        url="/login", 
        status_code=status.HTTP_302_FOUND
    )

@public_router.get("/logout")
def logout():
    """Log out by clearing the authentication cookie."""
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(key="access_token")
    return response

@protected_router.get("/profile", response_class=HTMLResponse)
def profile_page(request: Request, current_user: User = Depends(get_current_active_user)):
    """Render the user profile page."""
    return render_template(
        "profile.html", 
        {"request": request, "user": current_user}
    )

@public_router.get("/api/auth/session-check")
def check_session_status(
    access_token: Optional[str] = Cookie(None),
    db: PgConnection = Depends(get_db)
):
    """
    Check if the current session is valid.
    Returns a JSON response with a valid flag.
    Used by the frontend to check if the session is still active.
    """
    if not access_token:
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"valid": False})
    
    # Extract the token from the "Bearer <token>" format
    if access_token.startswith("Bearer "):
        token = access_token[7:]
    else:
        token = access_token
    
    try:
        # Verify the token
        from app.auth import SECRET_KEY, ALGORITHM
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        
        if username is None:
            return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"valid": False})
            
        # Check if user exists
        user = crud.get_user_by_username(db, username)
        if user is None or not user.is_active:
            return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"valid": False})
            
        return JSONResponse(status_code=status.HTTP_200_OK, content={"valid": True})
    except JWTError:
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"valid": False})
