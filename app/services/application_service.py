from sqlalchemy.orm import Session
from sqlalchemy import and_
from uuid import UUID
from typing import Optional
from datetime import date

from app.models.application import Application
from app.schemas.application import ApplicationCreate, ApplicationUpdate


def get_all_applications(db: Session, user_id: UUID) -> list[Application]:
    return db.query(Application).filter(Application.user_id == user_id).order_by(Application.applied_at.desc()).all()


def get_applications_by_status(db: Session, user_id: UUID, status: str) -> list[Application]:
    return db.query(Application).filter(
        and_(Application.user_id == user_id, Application.status == status)
    ).order_by(Application.applied_at.desc()).all()


def get_application_by_id(db: Session, user_id: UUID, application_id: UUID) -> Optional[Application]:
    return db.query(Application).filter(
        and_(Application.user_id == user_id, Application.id == application_id)
    ).first()


def create_application(db: Session, user_id: UUID, application: ApplicationCreate) -> Application:
    db_application = Application(
        user_id=user_id,
        company=application.company,
        role=application.role,
        job_url=application.job_url,
        job_id=application.job_id,
        location=application.location,
        resume_config=application.resume_config,
        applied_at=application.applied_at,
        notes=application.notes,
        referral=application.referral,
        salary_range=application.salary_range,
    )
    db.add(db_application)
    db.commit()
    db.refresh(db_application)
    return db_application


def update_application(
    db: Session, user_id: UUID, application_id: UUID, application: ApplicationUpdate
) -> Optional[Application]:
    db_application = get_application_by_id(db, user_id, application_id)
    if not db_application:
        return None

    update_data = application.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_application, field, value)

    db.commit()
    db.refresh(db_application)
    return db_application


def delete_application(db: Session, user_id: UUID, application_id: UUID) -> bool:
    db_application = get_application_by_id(db, user_id, application_id)
    if not db_application:
        return False

    db.delete(db_application)
    db.commit()
    return True