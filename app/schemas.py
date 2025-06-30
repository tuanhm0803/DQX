from pydantic import BaseModel, EmailStr, Field
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

class SQLExecuteRequest(BaseModel):
    script_content: str

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
        
# --- User Authentication Schemas ---

class UserBase(BaseModel):
    username: str
    email: str = Field(..., description="User email address")
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="User password, minimum 8 characters")

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None

class UserInDB(UserBase):
    id: int
    hashed_password: str
    is_active: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class User(UserBase):
    id: int
    is_active: bool

    class Config:
        orm_mode = True

class TokenData(BaseModel):
    username: Optional[str] = None