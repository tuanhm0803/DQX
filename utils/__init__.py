"""
DQX Utilities Package

This package contains utility modules for the DQX application.
"""

# Import logging functions for easier access
from .logger import (
    log_chat,
    read_chat_logs,
    clear_chat_logs,
    get_chat_log_path
)

# Version information
__version__ = "1.0.0"
