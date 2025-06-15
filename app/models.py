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