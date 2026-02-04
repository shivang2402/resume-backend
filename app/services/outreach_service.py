from sqlalchemy.orm import Session
from fastapi import HTTPException
from typing import List
from uuid import UUID

from app.models.outreach_template import OutreachTemplate
from app.schemas.outreach import TemplateCreate, TemplateUpdate


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
