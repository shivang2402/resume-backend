from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.database import get_db
from app.schemas.outreach import (
    TemplateCreate, TemplateUpdate, TemplateResponse
)
from app.services.outreach_service import OutreachService

router = APIRouter()


# ============ TEMPLATES ============

@router.get("/templates", response_model=List[TemplateResponse])
def list_templates(
    user_id: UUID = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    """List all templates for user"""
    return OutreachService.list_templates(db, user_id)


@router.post("/templates", response_model=TemplateResponse, status_code=201)
def create_template(
    data: TemplateCreate,
    user_id: UUID = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    """Create a new template"""
    return OutreachService.create_template(db, user_id, data)


@router.get("/templates/{template_id}", response_model=TemplateResponse)
def get_template(
    template_id: UUID,
    user_id: UUID = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    """Get a single template"""
    return OutreachService.get_template(db, user_id, template_id)


@router.put("/templates/{template_id}", response_model=TemplateResponse)
def update_template(
    template_id: UUID,
    data: TemplateUpdate,
    user_id: UUID = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    """Update a template"""
    return OutreachService.update_template(db, user_id, template_id, data)


@router.delete("/templates/{template_id}")
def delete_template(
    template_id: UUID,
    user_id: UUID = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    """Delete a template"""
    OutreachService.delete_template(db, user_id, template_id)
    return {"status": "deleted"}
