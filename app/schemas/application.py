from datetime import date, datetime
from uuid import UUID
from typing import Optional, Any

from pydantic import BaseModel


class ApplicationCreate(BaseModel):
    company: str
    role: str
    job_url: Optional[str] = None
    job_id: Optional[str] = None
    location: Optional[str] = None
    resume_config: dict[str, Any]
    applied_at: date
    notes: Optional[str] = None
    referral: Optional[str] = None
    salary_range: Optional[str] = None


class ApplicationUpdate(BaseModel):
    company: Optional[str] = None
    role: Optional[str] = None
    job_url: Optional[str] = None
    job_id: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    referral: Optional[str] = None
    salary_range: Optional[str] = None


class ApplicationResponse(BaseModel):
    id: UUID
    user_id: UUID
    company: str
    role: str
    job_url: Optional[str] = None
    job_id: Optional[str] = None
    location: Optional[str] = None
    status: str
    resume_config: dict[str, Any]
    applied_at: date
    created_at: datetime
    updated_at: datetime
    notes: Optional[str] = None
    referral: Optional[str] = None
    salary_range: Optional[str] = None

    class Config:
        from_attributes = True