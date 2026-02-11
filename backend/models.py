from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

# User Models
class UserBase(BaseModel):
    email: EmailStr
    username: str

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(UserBase):
    id: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: User

# Project Models
class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None

class ProjectCreate(ProjectBase):
    pass

class Project(ProjectBase):
    id: str
    user_id: str
    created_at: datetime
    document_count: int = 0
    
    class Config:
        from_attributes = True

# Document Models
class DocumentBase(BaseModel):
    filename: str
    file_size: int

class Document(DocumentBase):
    id: str
    project_id: str
    uploaded_at: datetime
    processed: bool = False
    
    class Config:
        from_attributes = True

# Query Models
class QueryRequest(BaseModel):
    question: str
    project_id: str
    use_memory: bool = True
    session_id: Optional[str] = None

class QueryResponse(BaseModel):
    answer: str
    sources: List[str] = []
    session_id: str
    timestamp: datetime

# Visualization Models
class GraphVisualization(BaseModel):
    nodes: List[dict]
    edges: List[dict]
    statistics: dict
