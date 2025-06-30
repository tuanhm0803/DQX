"""
Authentication routes for DQX
"""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, Form, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse, RedirectResponse
from psycopg2.extensions import connection as PgConnection

from app import crud
from app.auth import authenticate_user, create_access_token, get_current_active_user
from app.database import get_db
from app.dependencies import templates, render_template
from app.models import User
from app.schemas import Token, UserCreate

# Constants
ACCESS_TOKEN_EXPIRE_MINUTES = 30

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
    """Render the registration page."""
    return render_template("register.html", {"request": request})

@public_router.post("/register", response_class=HTMLResponse)
def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    full_name: str = Form(None),
    db: PgConnection = Depends(get_db)
):
    """Process registration form submission."""
    # Validate password match
    if password != confirm_password:
        return render_template(
            "register.html", 
            {
                "request": request, 
                "error": "Passwords don't match",
                "username": username,
                "email": email,
                "full_name": full_name
            },
            status_code=400
        )
    
    # Validate password length
    if len(password) < 8:
        return render_template(
            "register.html", 
            {
                "request": request, 
                "error": "Password must be at least 8 characters",
                "username": username,
                "email": email,
                "full_name": full_name
            },
            status_code=400
        )
    
    # Check if username or email already exists
    if crud.get_user_by_username(db, username):
        return render_template(
            "register.html", 
            {
                "request": request, 
                "error": f"Username '{username}' already exists",
                "email": email,
                "full_name": full_name
            },
            status_code=400
        )
        
    if crud.get_user_by_email(db, email):
        return render_template(
            "register.html", 
            {
                "request": request, 
                "error": f"Email '{email}' already exists",
                "username": username,
                "full_name": full_name
            },
            status_code=400
        )
    
    try:
        # Create new user
        crud.create_user(db, username, email, password, full_name)
        
        # Redirect to login page
        return RedirectResponse(
            url="/login?next=/", 
            status_code=status.HTTP_302_FOUND
        )
    except Exception as e:
        return render_template(
            "register.html", 
            {
                "request": request, 
                "error": f"Registration failed: {str(e)}",
                "username": username,
                "email": email,
                "full_name": full_name
            },
            status_code=400
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
