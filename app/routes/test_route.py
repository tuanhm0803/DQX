"""
Simple test route to diagnose template issues
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.dependencies import render_template

test_router = APIRouter()

@test_router.get("/test", response_class=HTMLResponse, tags=["Test"])
async def test_template(request: Request):
    """Simple test route"""
    return render_template("test_template.html", {"request": request})
