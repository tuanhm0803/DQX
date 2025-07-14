"""
Role-based access control for DQX application
This module provides functions to check user permissions based on their roles
"""

from fastapi import HTTPException, status, Depends
from app.dependencies_auth import get_current_user_from_cookie

def check_admin_access(user = Depends(get_current_user_from_cookie)):
    """
    Verify that the user has admin role.
    Raises HTTPException if user is not an admin.
    """
    if not user or user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this resource. Admin role required."
        )
    return user

def check_creator_access(user = Depends(get_current_user_from_cookie)):
    """
    Verify that the user has creator or admin role.
    Raises HTTPException if user does not have sufficient privileges.
    """
    if not user or (user.role not in ["admin", "creator"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this resource. Creator or admin role required."
        )
    return user

def can_create_table(user = Depends(get_current_user_from_cookie)):
    """
    Check if user can create tables (admin or creator roles)
    """
    if not user or (user.role not in ["admin", "creator"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to create tables. Creator or admin role required."
        )
    return user

def can_insert_data(user = Depends(get_current_user_from_cookie)):
    """
    Check if user can insert data (admin or creator roles)
    """
    if not user or (user.role not in ["admin", "creator"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to insert data. Creator or admin role required."
        )
    return user

def can_manage_users(user = Depends(get_current_user_from_cookie)):
    """
    Check if user can manage users (admin role only)
    """
    if not user or user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to manage users. Admin role required."
        )
    return user

def can_publish_populate(user = Depends(get_current_user_from_cookie)):
    """
    Check if user can publish/populate scripts (admin or creator roles only)
    Inputters cannot perform these operations
    """
    if not user or (user.role not in ["admin", "creator"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to publish or populate data. Creator or admin role required."
        )
    return user

def can_access_source_management(user = Depends(get_current_user_from_cookie)):
    """
    Check if user can access source data management (admin or creator roles only)
    Inputters cannot access this functionality
    """
    if not user or (user.role not in ["admin", "creator"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access source data management. Creator or admin role required."
        )
    return user

def can_delete_scripts(user = Depends(get_current_user_from_cookie)):
    """
    Check if user can delete SQL scripts (admin or creator roles only)
    Inputters cannot delete scripts
    """
    if not user or (user.role not in ["admin", "creator"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete scripts. Creator or admin role required."
        )
    return user

def can_delete_schedules(user = Depends(get_current_user_from_cookie)):
    """
    Check if user can delete scheduled jobs (admin or creator roles only)
    Inputters cannot delete schedules
    """
    if not user or (user.role not in ["admin", "creator"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete scheduled jobs. Creator or admin role required."
        )
    return user

def can_view_logs(user = Depends(get_current_user_from_cookie)):
    """
    Verify that the user can view action logs (admin or editor role).
    Raises HTTPException if user does not have sufficient privileges.
    """
    if not user or (user.role not in ["admin", "editor"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view logs. Admin or editor role required."
        )
    return user
