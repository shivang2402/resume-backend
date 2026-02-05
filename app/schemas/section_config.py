from pydantic import BaseModel, field_validator
from typing import Optional
from uuid import UUID
from datetime import datetime

class SectionConfigBase(BaseModel):
    priority: str = "normal"
    fixed_flavor: Optional[str] = None
    
    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v):
        if v not in ['always', 'normal', 'never']:
            raise ValueError('priority must be always, normal, or never')
        return v

class SectionConfigCreate(SectionConfigBase):
    section_type: str
    section_key: str

class SectionConfigUpdate(SectionConfigBase):
    pass

class SectionConfigResponse(SectionConfigBase):
    id: Optional[UUID] = None
    section_type: str
    section_key: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
