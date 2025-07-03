from typing import Optional
from datetime import datetime

# Sample model - you can expand this with your actual models
class ExampleTable:
    id: int
    name: str
    description: Optional[str]

    def __init__(self, name: str, description: Optional[str] = None, id: Optional[int] = None):
        self.id = id
        self.name = name
        self.description = description

class SQLScript:
    # Placeholder if other parts of your application expect this class
    # This is NOT an ORM model anymore
    id: int
    name: str
    description: Optional[str]
    content: str
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    def __init__(self, name: str, content: str, description: Optional[str] = None, id: Optional[int] = None, created_at: Optional[datetime] = None, updated_at: Optional[datetime] = None):
        self.id = id
        self.name = name
        self.description = description
        self.content = content
        self.created_at = created_at
        self.updated_at = updated_at

class User:
    """User model for authentication"""
    id: int
    username: str
    email: str
    full_name: Optional[str]
    hashed_password: str
    is_active: bool
    role: str  # 'admin', 'creator', or 'inputter'
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    def __init__(self, username: str, email: str, hashed_password: str, 
                full_name: Optional[str] = None, id: Optional[int] = None,
                is_active: bool = True, role: str = "inputter", 
                created_at: Optional[datetime] = None, updated_at: Optional[datetime] = None):
        self.id = id if id is not None else 0
        self.username = username
        self.email = email
        self.full_name = full_name
        self.hashed_password = hashed_password
        self.is_active = is_active
        self.role = role
        self.created_at = created_at
        self.updated_at = updated_at