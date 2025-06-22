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

# --- Schedule Schemas ---

class ScheduleBase(BaseModel):
    job_name: str
    script_id: int
    cron_schedule: str
    is_active: bool = True

class ScheduleCreate(ScheduleBase):
    pass

class ScheduleUpdate(BaseModel):
    job_name: Optional[str] = None
    script_id: Optional[int] = None
    cron_schedule: Optional[str] = None
    is_active: Optional[bool] = None

class Schedule(ScheduleBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True