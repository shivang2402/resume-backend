from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException
from typing import List
from uuid import UUID

from app.models.outreach_template import OutreachTemplate
from app.models.outreach_thread import OutreachThread
from app.models.outreach_message import OutreachMessage
from app.models.application import Application
from app.schemas.outreach import (
    TemplateCreate, TemplateUpdate,
    ThreadCreate, ThreadUpdate,
    MessageCreate
)


class OutreachService:

    # ============ TEMPLATES ============

    @staticmethod
    def list_templates(db: Session, user_id: UUID) -> List[OutreachTemplate]:
        return db.query(OutreachTemplate)\
            .filter(OutreachTemplate.user_id == user_id)\
            .order_by(OutreachTemplate.style, OutreachTemplate.length, OutreachTemplate.name)\
            .all()

    @staticmethod
    def create_template(db: Session, user_id: UUID, data: TemplateCreate) -> OutreachTemplate:
        template = OutreachTemplate(
            user_id=user_id,
            name=data.name,
            content=data.content,
            style=data.style.value,
            length=data.length.value
        )
        db.add(template)
        db.commit()
        db.refresh(template)
        return template

    @staticmethod
    def get_template(db: Session, user_id: UUID, template_id: UUID) -> OutreachTemplate:
        template = db.query(OutreachTemplate)\
            .filter(OutreachTemplate.id == template_id, OutreachTemplate.user_id == user_id)\
            .first()
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        return template

    @staticmethod
    def update_template(db: Session, user_id: UUID, template_id: UUID, data: TemplateUpdate) -> OutreachTemplate:
        template = db.query(OutreachTemplate)\
            .filter(OutreachTemplate.id == template_id, OutreachTemplate.user_id == user_id)\
            .first()
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                setattr(template, field, value.value if hasattr(value, 'value') else value)

        db.commit()
        db.refresh(template)
        return template

    @staticmethod
    def delete_template(db: Session, user_id: UUID, template_id: UUID):
        template = db.query(OutreachTemplate)\
            .filter(OutreachTemplate.id == template_id, OutreachTemplate.user_id == user_id)\
            .first()
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        db.delete(template)
        db.commit()

    # ============ THREADS ============

    @staticmethod
    def list_threads(db: Session, user_id: UUID, active_only: bool = False) -> List[dict]:
        query = db.query(OutreachThread).filter(OutreachThread.user_id == user_id)

        if active_only:
            query = query.filter(OutreachThread.is_active == True)

        threads = query.order_by(OutreachThread.updated_at.desc()).all()

        result = []
        for thread in threads:
            msg_count = db.query(func.count(OutreachMessage.id))\
                .filter(OutreachMessage.thread_id == thread.id).scalar()
            last_msg = db.query(OutreachMessage)\
                .filter(OutreachMessage.thread_id == thread.id)\
                .order_by(OutreachMessage.created_at.desc())\
                .first()

            result.append({
                "id": thread.id,
                "user_id": thread.user_id,
                "company": thread.company,
                "contact_name": thread.contact_name,
                "contact_method": thread.contact_method,
                "resume_config": thread.resume_config,
                "is_active": thread.is_active,
                "application_ids": [a.id for a in thread.applications],
                "message_count": msg_count,
                "last_message_at": last_msg.created_at if last_msg else None,
                "created_at": thread.created_at,
                "updated_at": thread.updated_at
            })

        return result

    @staticmethod
    def create_thread(db: Session, user_id: UUID, data: ThreadCreate) -> dict:
        thread = OutreachThread(
            user_id=user_id,
            company=data.company,
            contact_name=data.contact_name,
            contact_method=data.contact_method.value if data.contact_method else None,
            resume_config=data.resume_config
        )

        if data.application_ids:
            apps = db.query(Application)\
                .filter(Application.id.in_(data.application_ids), Application.user_id == user_id)\
                .all()
            thread.applications = apps

        db.add(thread)
        db.commit()
        db.refresh(thread)

        return {
            "id": thread.id,
            "user_id": thread.user_id,
            "company": thread.company,
            "contact_name": thread.contact_name,
            "contact_method": thread.contact_method,
            "resume_config": thread.resume_config,
            "is_active": thread.is_active,
            "application_ids": [a.id for a in thread.applications],
            "message_count": 0,
            "last_message_at": None,
            "created_at": thread.created_at,
            "updated_at": thread.updated_at
        }

    @staticmethod
    def get_thread(db: Session, user_id: UUID, thread_id: UUID) -> dict:
        thread = db.query(OutreachThread)\
            .filter(OutreachThread.id == thread_id, OutreachThread.user_id == user_id)\
            .first()
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")

        msg_count = db.query(func.count(OutreachMessage.id))\
            .filter(OutreachMessage.thread_id == thread.id).scalar()
        last_msg = db.query(OutreachMessage)\
            .filter(OutreachMessage.thread_id == thread.id)\
            .order_by(OutreachMessage.created_at.desc())\
            .first()

        return {
            "id": thread.id,
            "user_id": thread.user_id,
            "company": thread.company,
            "contact_name": thread.contact_name,
            "contact_method": thread.contact_method,
            "resume_config": thread.resume_config,
            "is_active": thread.is_active,
            "application_ids": [a.id for a in thread.applications],
            "message_count": msg_count,
            "last_message_at": last_msg.created_at if last_msg else None,
            "created_at": thread.created_at,
            "updated_at": thread.updated_at
        }

    @staticmethod
    def update_thread(db: Session, user_id: UUID, thread_id: UUID, data: ThreadUpdate) -> dict:
        thread = db.query(OutreachThread)\
            .filter(OutreachThread.id == thread_id, OutreachThread.user_id == user_id)\
            .first()
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")

        update_data = data.model_dump(exclude_unset=True)

        if "application_ids" in update_data and update_data["application_ids"] is not None:
            apps = db.query(Application)\
                .filter(Application.id.in_(update_data["application_ids"]), Application.user_id == user_id)\
                .all()
            thread.applications = apps
            del update_data["application_ids"]

        for field, value in update_data.items():
            if value is not None:
                setattr(thread, field, value.value if hasattr(value, 'value') else value)

        db.commit()
        db.refresh(thread)

        msg_count = db.query(func.count(OutreachMessage.id))\
            .filter(OutreachMessage.thread_id == thread.id).scalar()
        last_msg = db.query(OutreachMessage)\
            .filter(OutreachMessage.thread_id == thread.id)\
            .order_by(OutreachMessage.created_at.desc())\
            .first()

        return {
            "id": thread.id,
            "user_id": thread.user_id,
            "company": thread.company,
            "contact_name": thread.contact_name,
            "contact_method": thread.contact_method,
            "resume_config": thread.resume_config,
            "is_active": thread.is_active,
            "application_ids": [a.id for a in thread.applications],
            "message_count": msg_count,
            "last_message_at": last_msg.created_at if last_msg else None,
            "created_at": thread.created_at,
            "updated_at": thread.updated_at
        }

    @staticmethod
    def delete_thread(db: Session, user_id: UUID, thread_id: UUID):
        thread = db.query(OutreachThread)\
            .filter(OutreachThread.id == thread_id, OutreachThread.user_id == user_id)\
            .first()
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")
        db.delete(thread)
        db.commit()

    # ============ MESSAGES ============

    @staticmethod
    def list_messages(db: Session, user_id: UUID, thread_id: UUID) -> List[OutreachMessage]:
        thread = db.query(OutreachThread)\
            .filter(OutreachThread.id == thread_id, OutreachThread.user_id == user_id)\
            .first()
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")

        return db.query(OutreachMessage)\
            .filter(OutreachMessage.thread_id == thread_id)\
            .order_by(OutreachMessage.created_at.asc())\
            .all()

    @staticmethod
    def add_message(db: Session, user_id: UUID, thread_id: UUID, data: MessageCreate) -> OutreachMessage:
        thread = db.query(OutreachThread)\
            .filter(OutreachThread.id == thread_id, OutreachThread.user_id == user_id)\
            .first()
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")

        message = OutreachMessage(
            thread_id=thread_id,
            direction=data.direction.value,
            content=data.content,
            message_at=data.message_at
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        return message

    @staticmethod
    def delete_message(db: Session, user_id: UUID, thread_id: UUID, message_id: UUID):
        thread = db.query(OutreachThread)\
            .filter(OutreachThread.id == thread_id, OutreachThread.user_id == user_id)\
            .first()
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")

        message = db.query(OutreachMessage)\
            .filter(OutreachMessage.id == message_id, OutreachMessage.thread_id == thread_id)\
            .first()
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")

        db.delete(message)
        db.commit()

    # ============ UTILITY ============

    @staticmethod
    def get_applications_by_company(db: Session, user_id: UUID, company: str) -> List[dict]:
        apps = db.query(Application)\
            .filter(Application.user_id == user_id, Application.company.ilike(f"%{company}%"))\
            .all()

        return [
            {
                "id": a.id,
                "company": a.company,
                "role": a.role,
                "status": a.status,
                "applied_at": a.applied_at
            }
            for a in apps
        ]
