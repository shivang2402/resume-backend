from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime


class ResumePresetCreate(BaseModel):
    name: str
    resume_config: Dict[str, Any]  # {experiences: [...], projects: [...], skills: "..."}


class ResumePresetUpdate(BaseModel):
    name: Optional[str] = None
    resume_config: Optional[Dict[str, Any]] = None


class ResumePresetResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    resume_config: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
