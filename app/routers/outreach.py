from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.database import get_db
from app.schemas.outreach import (
    TemplateCreate, TemplateUpdate, TemplateResponse,
    ThreadCreate, ThreadUpdate, ThreadResponse,
    MessageCreate, MessageResponse,
    GenerateMessageRequest, GenerateMessageResponse,
    RefineMessageRequest, RefineMessageResponse,
    ParseConversationRequest, ParseConversationResponse,
    GenerateReplyRequest, GenerateReplyResponse
)
from app.services.outreach_service import OutreachService
from app.services.ai_outreach_service import AIOutreachService

router = APIRouter()


# ============ TEMPLATES ============

@router.get("/templates", response_model=List[TemplateResponse])
def list_templates(
    user_id: UUID = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    """List all templates for user."""
    return OutreachService.list_templates(db, user_id)


@router.post("/templates", response_model=TemplateResponse)
def create_template(
    data: TemplateCreate,
    user_id: UUID = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    """Create a new template."""
    return OutreachService.create_template(db, user_id, data)


@router.get("/templates/{template_id}", response_model=TemplateResponse)
def get_template(
    template_id: UUID,
    user_id: UUID = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    """Get a single template."""
    return OutreachService.get_template(db, user_id, template_id)


@router.put("/templates/{template_id}", response_model=TemplateResponse)
def update_template(
    template_id: UUID,
    data: TemplateUpdate,
    user_id: UUID = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    """Update a template."""
    return OutreachService.update_template(db, user_id, template_id, data)


@router.delete("/templates/{template_id}")
def delete_template(
    template_id: UUID,
    user_id: UUID = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    """Delete a template."""
    OutreachService.delete_template(db, user_id, template_id)
    return {"status": "deleted"}


# ============ THREADS ============

@router.get("/threads", response_model=List[ThreadResponse])
def list_threads(
    active_only: bool = Query(False),
    user_id: UUID = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    """List all threads, optionally filtered by active status."""
    return OutreachService.list_threads(db, user_id, active_only)


@router.post("/threads", response_model=ThreadResponse)
def create_thread(
    data: ThreadCreate,
    user_id: UUID = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    """Create a new thread."""
    return OutreachService.create_thread(db, user_id, data)


@router.get("/threads/{thread_id}", response_model=ThreadResponse)
def get_thread(
    thread_id: UUID,
    user_id: UUID = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    """Get a single thread with details."""
    return OutreachService.get_thread(db, user_id, thread_id)


@router.put("/threads/{thread_id}", response_model=ThreadResponse)
def update_thread(
    thread_id: UUID,
    data: ThreadUpdate,
    user_id: UUID = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    """Update a thread."""
    return OutreachService.update_thread(db, user_id, thread_id, data)


@router.delete("/threads/{thread_id}")
def delete_thread(
    thread_id: UUID,
    user_id: UUID = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    """Delete a thread and all its messages."""
    OutreachService.delete_thread(db, user_id, thread_id)
    return {"status": "deleted"}


# ============ MESSAGES ============

@router.get("/threads/{thread_id}/messages", response_model=List[MessageResponse])
def list_messages(
    thread_id: UUID,
    user_id: UUID = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    """List all messages in a thread."""
    return OutreachService.list_messages(db, user_id, thread_id)


@router.post("/threads/{thread_id}/messages", response_model=MessageResponse)
def add_message(
    thread_id: UUID,
    data: MessageCreate,
    user_id: UUID = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    """Add a message to a thread."""
    return OutreachService.add_message(db, user_id, thread_id, data)


@router.delete("/threads/{thread_id}/messages/{message_id}")
def delete_message(
    thread_id: UUID,
    message_id: UUID,
    user_id: UUID = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    """Delete a message from a thread."""
    OutreachService.delete_message(db, user_id, thread_id, message_id)
    return {"status": "deleted"}


# ============ AI GENERATION ============

@router.post("/generate", response_model=GenerateMessageResponse)
def generate_message(
    data: GenerateMessageRequest,
    user_id: UUID = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    """Generate a new outreach message using AI."""
    return AIOutreachService.generate_message(
        db=db,
        user_id=user_id,
        template_id=data.template_id,
        company=data.company,
        contact_name=data.contact_name,
        style=data.style.value if data.style else None,
        length=data.length.value if data.length else None,
        jd_text=data.jd_text,
        application_id=data.application_id,
        api_key=data.api_key
    )


@router.post("/refine", response_model=RefineMessageResponse)
def refine_message(
    data: RefineMessageRequest,
    api_key: str = Header(..., alias="X-Gemini-API-Key")
):
    """Refine an existing message with user instructions."""
    result = AIOutreachService.refine_message(
        original_message=data.original_message,
        refinement_instructions=data.refinement_instructions,
        style=data.style.value if data.style else None,
        length=data.length.value if data.length else None,
        api_key=api_key
    )
    return result


@router.post("/parse-conversation", response_model=ParseConversationResponse)
def parse_conversation(
    data: ParseConversationRequest,
    api_key: str = Header(..., alias="X-Gemini-API-Key")
):
    """Parse a raw conversation dump into structured messages."""
    result = AIOutreachService.parse_conversation(
        raw_text=data.raw_text,
        api_key=api_key
    )
    return result


@router.post("/generate-reply", response_model=GenerateReplyResponse)
def generate_reply(
    data: GenerateReplyRequest,
    user_id: UUID = Header(..., alias="X-User-ID"),
    api_key: str = Header(..., alias="X-Gemini-API-Key"),
    db: Session = Depends(get_db)
):
    """Generate a reply for an ongoing thread conversation."""
    result = AIOutreachService.generate_reply(
        db=db,
        user_id=user_id,
        thread_id=data.thread_id,
        instructions=data.instructions,
        style=data.style.value if data.style else "semi_formal",
        length=data.length.value if data.length else "long",
        api_key=api_key
    )
    return result


# ============ UTILITY ============

@router.get("/applications-by-company")
def get_applications_by_company(
    company: str = Query(...),
    user_id: UUID = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    """Get applications matching a company name (fuzzy match for auto-detect)."""
    return OutreachService.get_applications_by_company(db, user_id, company)
