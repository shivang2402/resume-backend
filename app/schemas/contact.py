from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class ContactField(BaseModel):
    label: str
    value: str


class ContactCreate(BaseModel):
    name: str
    fields: List[ContactField] = []


class ContactUpdate(BaseModel):
    name: Optional[str] = None
    fields: Optional[List[ContactField]] = None


class ContactResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    fields: List[ContactField]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
