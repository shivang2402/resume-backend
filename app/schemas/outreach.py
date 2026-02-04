from datetime import datetime
from uuid import UUID
from typing import Optional, Any, List
from enum import Enum

from pydantic import BaseModel, Field


# Enums
class WritingStyle(str, Enum):
    PROFESSIONAL = "professional"
    SEMI_FORMAL = "semi_formal"
    CASUAL = "casual"
    FRIEND = "friend"


class MessageLength(str, Enum):
    SHORT = "short"
    LONG = "long"


class MessageDirection(str, Enum):
    SENT = "sent"
    RECEIVED = "received"


class ContactMethod(str, Enum):
    LINKEDIN = "linkedin"
    EMAIL = "email"
    OTHER = "other"


# Template Schemas
class TemplateCreate(BaseModel):
    name: str = Field(..., max_length=255)
    content: str
    style: WritingStyle
    length: MessageLength


class TemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    content: Optional[str] = None
    style: Optional[WritingStyle] = None
    length: Optional[MessageLength] = None


class TemplateResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    content: str
    style: WritingStyle
    length: MessageLength
    extra_data: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TemplateListResponse(BaseModel):
    id: UUID
    name: str
    content: str
    style: WritingStyle
    length: MessageLength
    created_at: datetime

    class Config:
        from_attributes = True


# Thread Schemas
class ThreadCreate(BaseModel):
    company: str = Field(..., max_length=255)
    contact_name: Optional[str] = Field(None, max_length=255)
    contact_method: Optional[ContactMethod] = None
    application_ids: Optional[list[UUID]] = None
    resume_config: Optional[dict[str, Any]] = None


class ThreadUpdate(BaseModel):
    company: Optional[str] = Field(None, max_length=255)
    contact_name: Optional[str] = Field(None, max_length=255)
    contact_method: Optional[ContactMethod] = None
    application_ids: Optional[list[UUID]] = None
    resume_config: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None


class ThreadResponse(BaseModel):
    id: UUID
    user_id: UUID
    company: str
    contact_name: Optional[str]
    contact_method: Optional[ContactMethod]
    resume_config: Optional[dict[str, Any]]
    is_active: bool
    application_ids: list[UUID]
    message_count: int
    last_message_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Message Schemas
class MessageCreate(BaseModel):
    direction: MessageDirection
    content: str
    message_at: Optional[datetime] = None


class MessageResponse(BaseModel):
    id: UUID
    thread_id: UUID
    direction: MessageDirection
    content: str
    message_at: Optional[datetime]
    is_raw_dump: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ============ AI GENERATION SCHEMAS ============

class GenerateMessageRequest(BaseModel):
    """Request to generate a new outreach message."""
    template_id: Optional[UUID] = None
    company: str
    contact_name: Optional[str] = None
    style: Optional[WritingStyle] = None
    length: Optional[MessageLength] = None
    jd_text: Optional[str] = None
    application_id: Optional[UUID] = None
    api_key: Optional[str] = None


class GenerateMessageResponse(BaseModel):
    """Response from generating a message."""
    message: str


class RefineMessageRequest(BaseModel):
    """Request to refine an existing message."""
    original_message: str
    refinement_instructions: str
    style: Optional[WritingStyle] = None
    length: Optional[MessageLength] = None


class RefineMessageResponse(BaseModel):
    """Response from refining a message."""
    message: str
    char_count: int


class ParseConversationRequest(BaseModel):
    """Request to parse a raw conversation dump."""
    raw_text: str


class ParsedMessage(BaseModel):
    """A single parsed message from a conversation."""
    direction: MessageDirection
    content: str
    message_at: Optional[datetime] = None


class ParseConversationResponse(BaseModel):
    """Response from parsing a conversation."""
    success: bool
    messages: List[ParsedMessage] = []
    raw_fallback: Optional[str] = None


class GenerateReplyRequest(BaseModel):
    """Request to generate a reply for a thread."""
    thread_id: UUID
    instructions: Optional[str] = None
    style: Optional[WritingStyle] = WritingStyle.SEMI_FORMAL
    length: Optional[MessageLength] = MessageLength.LONG


class GenerateReplyResponse(BaseModel):
    """Response from generating a reply."""
    message: str
    char_count: int
