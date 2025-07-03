"""
Routes for admin user management
"""
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from typing import Optional
from app.database import get_db
from psycopg2.extensions import connection as PgConnection
from app.dependencies import render_template
from app.user_crud import get_users, create_user, update_user, delete_user, get_user
from app.role_permissions import can_manage_users

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/users", response_class=HTMLResponse)
def user_management_page(
    request: Request,
    user = Depends(can_manage_users),
    db: PgConnection = Depends(get_db)
):
    """Render the user management page for admins"""
    users = get_users(db)
    return render_template(
        "admin/user_management.html",
        {"request": request, "users": users}
    )

@router.post("/users/create", response_class=HTMLResponse)
def create_user_admin(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    full_name: Optional[str] = Form(None),
    role: str = Form("inputter"),
    user = Depends(can_manage_users),
    db: PgConnection = Depends(get_db)
):
    """Create a new user as admin"""
    try:
        # Validate role
        if role not in ["admin", "creator", "inputter"]:
            raise ValueError(f"Invalid role: {role}")
            
        # Create user
        create_user(db, username, email, password, full_name, role)
        
        # Redirect back to user management
        return RedirectResponse(
            url="/admin/users", 
            status_code=302
        )
    except Exception as e:
        # Get all users for rendering the page
        users = get_users(db)
        # Show error on the same page
        return render_template(
            "admin/user_management.html",
            {
                "request": request, 
                "users": users,
                "error": f"Error creating user: {str(e)}",
                "username": username,
                "email": email,
                "full_name": full_name,
                "selected_role": role
            },
            status_code=400
        )

@router.post("/users/{user_id}/update", response_class=HTMLResponse)
def update_user_admin(
    request: Request,
    user_id: int,
    username: str = Form(...),
    email: str = Form(...),
    full_name: Optional[str] = Form(None),
    role: str = Form("inputter"),
    is_active: bool = Form(False),
    password: Optional[str] = Form(None),
    user = Depends(can_manage_users),
    db: PgConnection = Depends(get_db)
):
    """Update an existing user"""
    try:
        # Prepare update data
        update_data = {
            "username": username,
            "email": email,
            "full_name": full_name,
            "role": role,
            "is_active": is_active
        }
        
        # Add password only if provided
        if password:
            update_data["password"] = password
            
        # Update user
        updated_user = update_user(db, user_id, update_data)
        
        if not updated_user:
            raise ValueError(f"User with ID {user_id} not found")
            
        # Redirect back to user management
        return RedirectResponse(
            url="/admin/users", 
            status_code=302
        )
    except Exception as e:
        # Get all users for rendering the page
        users = get_users(db)
        # Show error on the same page
        return render_template(
            "admin/user_management.html",
            {
                "request": request, 
                "users": users,
                "error": f"Error updating user: {str(e)}",
            },
            status_code=400
        )

@router.post("/users/{user_id}/delete", response_class=HTMLResponse)
def delete_user_admin(
    request: Request,
    user_id: int,
    user = Depends(can_manage_users),
    db: PgConnection = Depends(get_db)
):
    """Delete an existing user"""
    try:
        # Prevent deleting yourself
        if user.id == user_id:
            raise ValueError("You cannot delete your own account")
            
        # Delete user
        success = delete_user(db, user_id)
        
        if not success:
            raise ValueError(f"User with ID {user_id} not found")
            
        # Redirect back to user management
        return RedirectResponse(
            url="/admin/users", 
            status_code=302
        )
    except Exception as e:
        # Get all users for rendering the page
        users = get_users(db)
        # Show error on the same page
        return render_template(
            "admin/user_management.html",
            {
                "request": request, 
                "users": users,
                "error": f"Error deleting user: {str(e)}",
            },
            status_code=400
        )
