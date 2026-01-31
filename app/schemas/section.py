from datetime import datetime
from uuid import UUID
from typing import Optional, Any

from pydantic import BaseModel


class SectionCreate(BaseModel):
    type: str           # experience, project, skills, coursework, education, heading
    key: str            # amazon, kambaz, systems_hft
    flavor: str         # systems, fullstack, default
    content: dict[str, Any]  # bullets, title, dates, etc.


class SectionUpdate(BaseModel):
    content: dict[str, Any]


class SectionResponse(BaseModel):
    id: UUID
    user_id: UUID
    type: str
    key: str
    flavor: str
    version: str
    content: dict[str, Any]
    is_current: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SectionListResponse(BaseModel):
    type: str
    key: str
    flavor: str
    current_version: str
    versions: list[str]