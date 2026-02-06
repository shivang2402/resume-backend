"""
Sections Router - CRUD with automatic tag generation.
Tags are generated when Gemini API key is provided via X-Gemini-API-Key header.
"""

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional, List

from app.database import get_db
from app.schemas.section import SectionCreate, SectionUpdate, SectionResponse
from app.services import section_service
from app.services.tag_generator import generate_section_tags

router = APIRouter()


def get_current_user_id(x_user_id: Optional[str] = Header(None, alias="X-User-Id")) -> UUID:
    """Extract user ID from header."""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header required")
    return UUID(x_user_id)


def get_gemini_api_key(x_gemini_api_key: Optional[str] = Header(None, alias="X-Gemini-API-Key")) -> Optional[str]:
    """Extract Gemini API key from header (optional)."""
    return x_gemini_api_key


async def generate_tags_for_content(api_key: Optional[str], content: dict, section_type: str) -> dict:
    """Generate tags for content if API key is available."""
    if not api_key:
        return content
    
    try:
        tags = await generate_section_tags(api_key, content, section_type)
        content['tags'] = tags
    except Exception as e:
        print(f"Tag generation failed: {e}")
        content['tags'] = []
    
    return content


@router.get("")
def list_sections(
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """List all sections for user."""
    sections = section_service.get_all_sections(db, user_id)
    return [SectionResponse.model_validate(s) for s in sections]


@router.get("/{type}")
def list_sections_by_type(
    type: str,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """List sections filtered by type."""
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
    """Get all versions of a specific section."""
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
    """Get a specific version of a section."""
    section = section_service.get_section_by_version(db, user_id, type, key, flavor, version)
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    return SectionResponse.model_validate(section)


@router.post("", status_code=201)
async def create_section(
    section: SectionCreate,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
    api_key: Optional[str] = Depends(get_gemini_api_key),
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
    
    content = await generate_tags_for_content(api_key, dict(section.content), section.type)
    
    section_with_tags = SectionCreate(
        type=section.type,
        key=section.key,
        flavor=section.flavor,
        content=content
    )
    new_section = section_service.create_section(db, user_id, section_with_tags)
    return SectionResponse.model_validate(new_section)


@router.post("/bulk", status_code=201)
async def bulk_create_sections(
    sections: List[SectionCreate],
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
    api_key: Optional[str] = Depends(get_gemini_api_key),
):
    """Bulk create sections with auto-generated tags."""
    import asyncio
    
    results = {"success": [], "failed": []}
    
    for i, section in enumerate(sections):
        # Add delay between API calls to avoid rate limits (100ms = max 600/min)
        if i > 0 and api_key:
            await asyncio.sleep(0.15)
        
        try:
            existing = section_service.get_current_section(
                db, user_id, section.type, section.key, section.flavor
            )
            if existing:
                results["failed"].append({
                    "key": section.key,
                    "error": "Section already exists"
                })
                continue
            
            content = await generate_tags_for_content(api_key, dict(section.content), section.type)
            
            section_with_tags = SectionCreate(
                type=section.type,
                key=section.key,
                flavor=section.flavor,
                content=content
            )
            new_section = section_service.create_section(db, user_id, section_with_tags)
            results["success"].append(SectionResponse.model_validate(new_section))
        except Exception as e:
            results["failed"].append({
                "key": section.key,
                "error": str(e)
            })
    
    return results


@router.put("/{type}/{key}/{flavor}")
async def update_section(
    type: str,
    key: str,
    flavor: str,
    section: SectionUpdate,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
    api_key: Optional[str] = Depends(get_gemini_api_key),
):
    """Update section with auto-generated tags."""
    content = await generate_tags_for_content(api_key, dict(section.content), type)
    
    section_with_tags = SectionUpdate(content=content)
    updated = section_service.update_section(db, user_id, type, key, flavor, section_with_tags)
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
    """Delete a specific version of a section."""
    deleted = section_service.delete_section_version(db, user_id, type, key, flavor, version)
    if not deleted:
        raise HTTPException(status_code=404, detail="Section not found")
    return None