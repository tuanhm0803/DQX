from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime

class GenericModel(BaseModel):
    data: Dict[str, Any]

class TableData(BaseModel):
    data: List[Dict[str, Any]]
    total: int
    skip: int
    limit: int

class Token(BaseModel):
    access_token: str
    token_type: str

class SQLScriptBase(BaseModel):
    name: str
    description: Optional[str] = None
    content: str
    
class SQLScriptCreate(SQLScriptBase):
    pass

class SQLScript(SQLScriptBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True