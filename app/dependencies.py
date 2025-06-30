"""
Shared dependencies for the DQX application
"""
import os
from typing import Dict, Any
from fastapi import Request, Depends
from fastapi.templating import Jinja2Templates

# Configure Jinja2 templates
templates_path = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_path)

# Create a custom TemplateResponse method to add the current user to all templates
def render_template(name: str, context: Dict[str, Any], status_code: int = 200):
    """
    Custom template renderer that adds the current user to all templates.
    """
    if "request" not in context:
        raise ValueError("Request object must be provided in the context")
    
    # Add the current user to the context if it exists
    request = context["request"]
    if hasattr(request.state, "user") and request.state.user:
        context["current_user"] = request.state.user
    else:
        context["current_user"] = None
    
    # Return the template response
    return templates.TemplateResponse(name=name, context=context, status_code=status_code)
