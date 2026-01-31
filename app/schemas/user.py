from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    provider: str
    provider_id: str


class UserResponse(BaseModel):
    id: UUID
    email: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    provider: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True