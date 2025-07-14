"""
Routes for user actions log and audit functionality.
"""

from fastapi import APIRouter, Request, Depends, Query, HTTPException
from fastapi.responses import HTMLResponse
from app import crud
from app.role_permissions import can_view_logs
from app.database import get_db
from app.dependencies import render_template
from typing import Optional
import json

router = APIRouter()


@router.get("/user-actions-log", response_class=HTMLResponse)
async def user_actions_log_page(
    request: Request,
    current_user=Depends(can_view_logs),
    db=Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),
    username: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None)
):
    """Display user actions log page with filtering options."""
    
    try:
        # Get filters
        filters = {}
        if username:
            filters['username'] = username
        if action:
            filters['action'] = action
        if resource_type:
            filters['resource_type'] = resource_type
        if date_from:
            filters['date_from'] = date_from
        if date_to:
            filters['date_to'] = date_to
        
        # Calculate offset
        offset = (page - 1) * limit
        
        # Get logs
        logs_result = crud.get_user_actions_log(
            db=db,
            limit=limit,
            offset=offset,
            filters=filters
        )
        
        logs = logs_result.get('logs', [])
        total_count = logs_result.get('total_count', 0)
        
        # Calculate pagination info
        total_pages = (total_count + limit - 1) // limit
        has_prev = page > 1
        has_next = page < total_pages
        
        # Get unique values for filter dropdowns
        unique_users = crud.get_user_actions_log(db=db, get_unique_usernames=True)
        unique_actions = crud.get_user_actions_log(db=db, get_unique_actions=True)
        unique_resource_types = crud.get_user_actions_log(db=db, get_unique_resource_types=True)
        
        return render_template("user_actions_log.html", {
            "request": request,
            "user": current_user,
            "logs": logs,
            "total_count": total_count,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "has_prev": has_prev,
            "has_next": has_next,
            "filters": {
                "username": username,
                "action": action,
                "resource_type": resource_type,
                "date_from": date_from,
                "date_to": date_to
            },
            "unique_users": unique_users.get('usernames', []),
            "unique_actions": unique_actions.get('actions', []),
            "unique_resource_types": unique_resource_types.get('resource_types', [])
        })
        
    except Exception as e:
        return render_template("error.html", {
            "request": request,
            "user": current_user,
            "error_message": f"Error loading user actions log: {str(e)}"
        })


@router.get("/api/user-actions-log")
async def get_user_actions_log_api(
    current_user=Depends(can_view_logs),
    db=Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),
    username: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None)
):
    """API endpoint for user actions log data."""
    
    try:
        # Get filters
        filters = {}
        if username:
            filters['username'] = username
        if action:
            filters['action'] = action
        if resource_type:
            filters['resource_type'] = resource_type
        if date_from:
            filters['date_from'] = date_from
        if date_to:
            filters['date_to'] = date_to
        
        # Calculate offset
        offset = (page - 1) * limit
        
        # Get logs
        result = crud.get_user_actions_log(
            db=db,
            limit=limit,
            offset=offset,
            filters=filters
        )
        
        return {
            "success": True,
            "data": result.get('logs', []),
            "total_count": result.get('total_count', 0),
            "page": page,
            "limit": limit,
            "total_pages": (result.get('total_count', 0) + limit - 1) // limit
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving logs: {str(e)}")
