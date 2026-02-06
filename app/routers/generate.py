from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import Response
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional
from datetime import date
import base64

from app.database import get_db
from app.services import generator_service, application_service
from app.schemas.application import ApplicationCreate
from pydantic import BaseModel


router = APIRouter()


class GenerateRequest(BaseModel):
    resume_config: dict
    # Optional: create application record
    job: Optional[dict] = None
    temp_edits: Optional[dict] = None
    temp_edits: Optional[dict] = None  # {company, role, location, job_url, job_id}


class GenerateResponse(BaseModel):
    pdf_base64: str
    application_id: Optional[str] = None


def get_current_user_id(x_user_id: Optional[str] = Header(None)) -> UUID:
    if not x_user_id:
        return UUID("00000000-0000-0000-0000-000000000001")
    return UUID(x_user_id)


@router.post("")
def generate_resume(
    request: GenerateRequest,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """
    Generate PDF resume and optionally create application record.
    Returns PDF as file download.
    """
    try:
        pdf_bytes = generator_service.generate_resume(db, user_id, request.resume_config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")
    
    # Create application record if job info provided
    application_id = None
    if request.job:
        app_data = ApplicationCreate(
            company=request.job.get("company", "Unknown"),
            role=request.job.get("role", "Unknown"),
            job_url=request.job.get("job_url"),
            job_id=request.job.get("job_id"),
            location=request.job.get("location"),
            resume_config=request.resume_config,
            applied_at=date.today(),
        )
        new_app = application_service.create_application(db, user_id, app_data)
        application_id = str(new_app.id)
    
    # Return PDF as file download
    headers = {
        "Content-Disposition": f"attachment; filename=resume.pdf"
    }
    if application_id:
        headers["X-Application-Id"] = application_id
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers=headers,
    )


@router.post("/preview")
def generate_preview(
    request: GenerateRequest,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """
    Generate PDF and return as base64 (for preview in browser).
    Does NOT create application record.
    """
    try:
        pdf_bytes = generator_service.generate_resume(db, user_id, request.resume_config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")
    
    pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
    
    return GenerateResponse(pdf_base64=pdf_base64)