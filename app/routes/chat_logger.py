"""
Routes for chat logging functionality
"""
from fastapi import APIRouter, Request, Body
from fastapi.responses import HTMLResponse
from utils.logger import log_chat
from app.dependencies import templates

# Router for HTML pages and API
router = APIRouter()

# HTML page route
@router.get("/chat_logger", response_class=HTMLResponse, tags=["Pages"])
async def chat_logger_page(request: Request):
    """
    Page for logging chat conversations.
    
    Args:
        request: The FastAPI request object
        
    Returns:
        HTML response with the chat logger page
    """
    return templates.TemplateResponse("chat_logger.html", {"request": request})

# API endpoint for logging chats
@router.post("/api/log_chat", tags=["API - Chat"])
async def log_chat_message(
    user_message: str = Body(..., embed=True),
    assistant_response: str = Body(..., embed=True)
):
    """
    Log chat conversations between the user and assistant.
    
    Args:
        user_message: The message from the user
        assistant_response: The response from the assistant
    
    Returns:
        A success message
    """
    try:
        log_chat(user_message, assistant_response)
        return {"status": "success", "message": "Chat logged successfully"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to log chat: {str(e)}"}
