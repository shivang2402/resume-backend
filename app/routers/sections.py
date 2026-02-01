from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional

from app.database import get_db
from app.schemas.section import SectionCreate, SectionUpdate, SectionResponse
from app.services import section_service

router = APIRouter()

# TODO: Replace with actual auth - for now use a header
def get_current_user_id(x_user_id: Optional[str] = None) -> UUID:
    if not x_user_id:
        # Default test user ID
        return UUID("00000000-0000-0000-0000-000000000001")
    return UUID(x_user_id)


@router.get("")
def list_sections(
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    sections = section_service.get_all_sections(db, user_id)
    return [SectionResponse.model_validate(s) for s in sections]


@router.get("/{type}")
def list_sections_by_type(
    type: str,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    sections = section_service.get_sections_by_type(db, user_id, type)
    return [SectionResponse.model_validate(s) for s in sections]


@router.get("/{type}/{key}/{flavor}")
def get_section_versions(
    type: str,
    key: str,
    flavor: str,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    sections = section_service.get_section_versions(db, user_id, type, key, flavor)
    return [SectionResponse.model_validate(s) for s in sections]


@router.get("/{type}/{key}/{flavor}/{version}")
def get_section_by_version(
    type: str,
    key: str,
    flavor: str,
    version: str,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    section = section_service.get_section_by_version(db, user_id, type, key, flavor, version)
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    return SectionResponse.model_validate(section)


@router.post("", status_code=201)
def create_section(
    section: SectionCreate,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    # Check if section already exists
    existing = section_service.get_current_section(
        db, user_id, section.type, section.key, section.flavor
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Section already exists. Use PUT to update.",
        )
    new_section = section_service.create_section(db, user_id, section)
    return SectionResponse.model_validate(new_section)


@router.put("/{type}/{key}/{flavor}")
def update_section(
    type: str,
    key: str,
    flavor: str,
    section: SectionUpdate,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    updated = section_service.update_section(db, user_id, type, key, flavor, section)
    if not updated:
        raise HTTPException(status_code=404, detail="Section not found")
    return SectionResponse.model_validate(updated)


@router.delete("/{type}/{key}/{flavor}/{version}", status_code=204)
def delete_section_version(
    type: str,
    key: str,
    flavor: str,
    version: str,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    deleted = section_service.delete_section_version(db, user_id, type, key, flavor, version)
    if not deleted:
        raise HTTPException(status_code=404, detail="Section not found")
    return None