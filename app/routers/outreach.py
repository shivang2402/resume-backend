from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.database import get_db
from app.schemas.outreach import (
    TemplateCreate, TemplateUpdate, TemplateResponse,
    ThreadCreate, ThreadUpdate, ThreadResponse,
    MessageCreate, MessageResponse
)
from app.services.outreach_service import OutreachService

router = APIRouter()


# ============ TEMPLATES ============

@router.get("/templates", response_model=List[TemplateResponse])
def list_templates(
    user_id: UUID = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    return OutreachService.list_templates(db, user_id)


@router.post("/templates", response_model=TemplateResponse, status_code=201)
def create_template(
    data: TemplateCreate,
    user_id: UUID = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    return OutreachService.create_template(db, user_id, data)


@router.get("/templates/{template_id}", response_model=TemplateResponse)
def get_template(
    template_id: UUID,
    user_id: UUID = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    return OutreachService.get_template(db, user_id, template_id)


@router.put("/templates/{template_id}", response_model=TemplateResponse)
def update_template(
    template_id: UUID,
    data: TemplateUpdate,
    user_id: UUID = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    return OutreachService.update_template(db, user_id, template_id, data)


@router.delete("/templates/{template_id}")
def delete_template(
    template_id: UUID,
    user_id: UUID = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    OutreachService.delete_template(db, user_id, template_id)
    return {"status": "deleted"}


# ============ THREADS ============

@router.get("/threads", response_model=List[ThreadResponse])
def list_threads(
    active_only: bool = False,
    user_id: UUID = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    return OutreachService.list_threads(db, user_id, active_only)


@router.post("/threads", response_model=ThreadResponse, status_code=201)
def create_thread(
    data: ThreadCreate,
    user_id: UUID = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    return OutreachService.create_thread(db, user_id, data)


@router.get("/threads/{thread_id}", response_model=ThreadResponse)
def get_thread(
    thread_id: UUID,
    user_id: UUID = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    return OutreachService.get_thread(db, user_id, thread_id)


@router.put("/threads/{thread_id}", response_model=ThreadResponse)
def update_thread(
    thread_id: UUID,
    data: ThreadUpdate,
    user_id: UUID = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    return OutreachService.update_thread(db, user_id, thread_id, data)


@router.delete("/threads/{thread_id}")
def delete_thread(
    thread_id: UUID,
    user_id: UUID = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    OutreachService.delete_thread(db, user_id, thread_id)
    return {"status": "deleted"}


# ============ MESSAGES ============

@router.get("/threads/{thread_id}/messages", response_model=List[MessageResponse])
def list_messages(
    thread_id: UUID,
    user_id: UUID = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    return OutreachService.list_messages(db, user_id, thread_id)


@router.post("/threads/{thread_id}/messages", response_model=MessageResponse, status_code=201)
def add_message(
    thread_id: UUID,
    data: MessageCreate,
    user_id: UUID = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    return OutreachService.add_message(db, user_id, thread_id, data)


@router.delete("/threads/{thread_id}/messages/{message_id}")
def delete_message(
    thread_id: UUID,
    message_id: UUID,
    user_id: UUID = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    OutreachService.delete_message(db, user_id, thread_id, message_id)
    return {"status": "deleted"}


# ============ UTILITY ============

@router.get("/applications-by-company")
def get_applications_by_company(
    company: str,
    user_id: UUID = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    return OutreachService.get_applications_by_company(db, user_id, company)


# ============ AI GENERATION ============

from app.schemas.outreach import (
    GenerateMessageRequest, GenerateReplyRequest, 
    RefineMessageRequest, GeneratedMessageResponse
)
from app.services.ai_outreach_service import AIOutreachService


@router.post("/generate", response_model=GeneratedMessageResponse)
def generate_message(
    data: GenerateMessageRequest,
    user_id: UUID = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    """Generate an initial outreach message using AI."""
    message = AIOutreachService.generate_initial_message(
        db=db,
        user_id=user_id,
        template_id=data.template_id,
        company=data.company,
        contact_name=data.contact_name,
        resume_config=data.resume_config,
        additional_context=data.additional_context,
        api_key=data.api_key
    )
    return {"message": message}


@router.post("/generate/reply", response_model=GeneratedMessageResponse)
def generate_reply(
    data: GenerateReplyRequest,
    user_id: UUID = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    """Generate a reply based on conversation history."""
    message = AIOutreachService.generate_reply(
        db=db,
        user_id=user_id,
        thread_id=data.thread_id,
        received_message=data.received_message,
        style=data.style.value if data.style else "professional",
        length=data.length.value if data.length else "short",
        additional_instructions=data.additional_instructions,
        api_key=data.api_key
    )
    return {"message": message}


@router.post("/generate/refine", response_model=GeneratedMessageResponse)
def refine_message(
    data: RefineMessageRequest,
    user_id: UUID = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    """Refine an existing message based on feedback."""
    message = AIOutreachService.refine_message(
        original_message=data.original_message,
        refinement_instructions=data.refinement_instructions,
        api_key=data.api_key
    )
    return {"message": message}
