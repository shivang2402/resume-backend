from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from app.database import get_db
from app.schemas.application import ApplicationCreate, ApplicationUpdate, ApplicationResponse
from app.services import application_service

router = APIRouter()

def get_current_user_id(x_user_id: Optional[str] = Header(None, alias="X-User-Id")) -> UUID:
    """Extract user ID from header."""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header required")
    return UUID(x_user_id)

@router.get("")
def list_applications(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    if status:
        applications = application_service.get_applications_by_status(db, user_id, status)
    else:
        applications = application_service.get_all_applications(db, user_id)
    return [ApplicationResponse.model_validate(a) for a in applications]

@router.get("/{application_id}")
def get_application(
    application_id: UUID,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    application = application_service.get_application_by_id(db, user_id, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    return ApplicationResponse.model_validate(application)

@router.post("")
def create_application(
    application: ApplicationCreate,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    new_application = application_service.create_application(db, user_id, application)
    return ApplicationResponse.model_validate(new_application)

@router.put("/{application_id}")
def update_application(
    application_id: UUID,
    application: ApplicationUpdate,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    updated = application_service.update_application(db, user_id, application_id, application)
    if not updated:
        raise HTTPException(status_code=404, detail="Application not found")
    return ApplicationResponse.model_validate(updated)

@router.delete("/{application_id}")
def delete_application(
    application_id: UUID,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    deleted = application_service.delete_application(db, user_id, application_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Application not found")
    return None
