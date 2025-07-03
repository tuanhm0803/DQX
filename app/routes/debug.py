"""
Debug routes for DQX
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from app.dependencies import render_template
from app.dependencies_auth import login_required

# Create router
router = APIRouter(tags=["Debug"])

@router.get("/debug", response_class=HTMLResponse)
def debug_page(request: Request, user = Depends(login_required)):
    """
    Debug page to show information about the current user and request state
    """
    return render_template(
        "debug.html",
        {"request": request}
    )
