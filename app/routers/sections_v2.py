"""
Sections Router V2 - With tag generation on create/update.
"""

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional

from app.database import get_db
from app.schemas.section import SectionCreate, SectionUpdate, SectionResponse
from app.services import section_service
from app.services.tag_generator import generate_section_tags

router = APIRouter()


def get_current_user_id(x_user_id: Optional[str] = None) -> UUID:
    if not x_user_id:
        return UUID("00000000-0000-0000-0000-000000000001")
    return UUID(x_user_id)


@router.post("", status_code=201)
async def create_section(
    section: SectionCreate,
    x_gemini_api_key: Optional[str] = Header(None, alias="X-Gemini-API-Key"),
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """Create section with auto-generated tags."""
    existing = section_service.get_current_section(
        db, user_id, section.type, section.key, section.flavor
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Section already exists. Use PUT to update.",
        )
    
    content = dict(section.content)
    if x_gemini_api_key:
        try:
            tags = await generate_section_tags(x_gemini_api_key, content, section.type)
            content['tags'] = tags
        except Exception as e:
            print(f"Tag generation failed: {e}")
            content['tags'] = []
    
    section_with_tags = SectionCreate(
        type=section.type,
        key=section.key,
        flavor=section.flavor,
        content=content
    )
    new_section = section_service.create_section(db, user_id, section_with_tags)
    return SectionResponse.model_validate(new_section)


@router.put("/{type}/{key}/{flavor}")
async def update_section(
    type: str,
    key: str,
    flavor: str,
    section: SectionUpdate,
    x_gemini_api_key: Optional[str] = Header(None, alias="X-Gemini-API-Key"),
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """Update section with auto-generated tags."""
    content = dict(section.content)
    if x_gemini_api_key:
        try:
            tags = await generate_section_tags(x_gemini_api_key, content, type)
            content['tags'] = tags
        except Exception as e:
            print(f"Tag generation failed: {e}")
            content['tags'] = []
    
    section_with_tags = SectionUpdate(content=content)
    updated = section_service.update_section(db, user_id, type, key, flavor, section_with_tags)
    if not updated:
        raise HTTPException(status_code=404, detail="Section not found")
    return SectionResponse.model_validate(updated)
