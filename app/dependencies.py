"""
Shared dependencies for the DQX application
"""
import os
from fastapi.templating import Jinja2Templates

# Configure Jinja2 templates
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))
