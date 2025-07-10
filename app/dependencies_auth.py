"""
Authentication dependencies for use in routes
"""
from typing import Optional
from fastapi import Cookie, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt

from app import auth
from app import crud
from app.database import get_db

# Constants - should match those in auth.py
SECRET_KEY = auth.SECRET_KEY
ALGORITHM = auth.ALGORITHM

def get_current_user_from_cookie(
    request: Request,
    access_token: Optional[str] = Cookie(None),
    db = Depends(get_db)
):
    """
    Get the current user from the cookie.
    If no user is found, return None.
    """
    if not access_token:
        return None
        
    # Extract the token from the "Bearer <token>" format
    if access_token.startswith("Bearer "):
        token = access_token[7:]
    else:
        token = access_token
        
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
    except JWTError:
        return None
        
    user = crud.get_user_by_username(db, username)
    if user is None:
        return None
        
    return user

def login_required(request: Request, user=Depends(get_current_user_from_cookie)):
    """
    Verify that the user is logged in.
    If not, redirect to the login page.
    """
    if user is None or not user.is_active:
        # Get the current path to redirect back after login
        path = request.url.path
        
        # Handle query parameters
        query = ""
        if request.url.query:
            # Check if query is already a string or needs decoding
            if isinstance(request.url.query, bytes):
                query = request.url.query.decode()
            else:
                query = str(request.url.query)
                
        full_path = f"{path}?{query}" if query else path
        
        # Don't redirect back to logout or auth paths
        if path == "/logout" or path.startswith("/login") or path.startswith("/register"):
            full_path = "/"
            
        return RedirectResponse(
            url=f"/login?next={full_path}",
            status_code=status.HTTP_302_FOUND
        )
    return user
