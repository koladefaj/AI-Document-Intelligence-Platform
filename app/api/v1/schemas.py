from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime

# --- AUTHENTICATION SCHEMES ---

class LoginRequest(BaseModel):
    """Schema for user login credentials."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=100)

class RegisterRequest(BaseModel):
    """Schema for new user registration."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=100)

class TokenResponse(BaseModel):
    """Schema returned after successful login."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

# --- DOCUMENT SCHEMES ---

class DocumentResponse(BaseModel):
    """
    Schema for returning document metadata to the frontend.
    Filters out sensitive internal paths.
    """
    id: UUID
    file_name: str
    status: str
    url: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True # Allows Pydantic to read SQLAlchemy models

class TaskStatusResponse(BaseModel):
    """Schema for background task updates."""
    task_id: str
    status: str
    is_completed: bool
    is_failed: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None