from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.database import get_db
from app.models.contact import Contact
from app.schemas.contact import ContactCreate, ContactUpdate, ContactResponse

router = APIRouter()


def get_current_user_id(x_user_id: str = Header(...)) -> UUID:
    return UUID(x_user_id)


@router.get("", response_model=List[ContactResponse])
def list_contacts(
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    contacts = (
        db.query(Contact)
        .filter(Contact.user_id == user_id)
        .order_by(Contact.updated_at.desc())
        .all()
    )
    return [ContactResponse.model_validate(c) for c in contacts]


@router.post("", response_model=ContactResponse, status_code=201)
def create_contact(
    contact: ContactCreate,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    new_contact = Contact(
        user_id=user_id,
        name=contact.name,
        fields=[f.model_dump() for f in contact.fields],
    )
    db.add(new_contact)
    db.commit()
    db.refresh(new_contact)
    return ContactResponse.model_validate(new_contact)


@router.get("/{contact_id}", response_model=ContactResponse)
def get_contact(
    contact_id: UUID,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    contact = db.query(Contact).filter(Contact.id == contact_id, Contact.user_id == user_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return ContactResponse.model_validate(contact)


@router.put("/{contact_id}", response_model=ContactResponse)
def update_contact(
    contact_id: UUID,
    contact: ContactUpdate,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    existing = db.query(Contact).filter(Contact.id == contact_id, Contact.user_id == user_id).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Contact not found")

    if contact.name is not None:
        existing.name = contact.name
    if contact.fields is not None:
        existing.fields = [f.model_dump() for f in contact.fields]

    db.commit()
    db.refresh(existing)
    return ContactResponse.model_validate(existing)


@router.delete("/{contact_id}", status_code=204)
def delete_contact(
    contact_id: UUID,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    existing = db.query(Contact).filter(Contact.id == contact_id, Contact.user_id == user_id).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Contact not found")

    db.delete(existing)
    db.commit()
    return None
