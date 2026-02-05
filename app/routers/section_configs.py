from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid

from app.database import get_db
from app.models.section_config import SectionConfig
from app.schemas.section_config import (
    SectionConfigCreate,
    SectionConfigUpdate,
    SectionConfigResponse
)

router = APIRouter()

def get_user_id(x_user_id: str = Header(...)) -> uuid.UUID:
    """Extract user ID from header."""
    try:
        return uuid.UUID(x_user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

@router.get("/", response_model=List[SectionConfigResponse])
def get_section_configs(
    user_id: uuid.UUID = Depends(get_user_id),
    db: Session = Depends(get_db)
):
    """Get all section configs for user."""
    configs = db.query(SectionConfig).filter(
        SectionConfig.user_id == user_id
    ).all()
    return configs

@router.get("/{section_type}/{section_key}", response_model=SectionConfigResponse)
def get_section_config(
    section_type: str,
    section_key: str,
    user_id: uuid.UUID = Depends(get_user_id),
    db: Session = Depends(get_db)
):
    """Get config for specific section."""
    config = db.query(SectionConfig).filter(
        SectionConfig.user_id == user_id,
        SectionConfig.section_type == section_type,
        SectionConfig.section_key == section_key
    ).first()
    
    if not config:
        # Return default config
        return SectionConfigResponse(
            section_type=section_type,
            section_key=section_key,
            priority="normal",
            fixed_flavor=None
        )
    return config

@router.put("/{section_type}/{section_key}", response_model=SectionConfigResponse)
def upsert_section_config(
    section_type: str,
    section_key: str,
    config_data: SectionConfigUpdate,
    user_id: uuid.UUID = Depends(get_user_id),
    db: Session = Depends(get_db)
):
    """Create or update section config."""
    
    # Validate: if priority is 'always', fixed_flavor is required
    if config_data.priority == "always" and not config_data.fixed_flavor:
        raise HTTPException(
            status_code=400, 
            detail="fixed_flavor required when priority is 'always'"
        )
    
    config = db.query(SectionConfig).filter(
        SectionConfig.user_id == user_id,
        SectionConfig.section_type == section_type,
        SectionConfig.section_key == section_key
    ).first()
    
    if config:
        config.priority = config_data.priority
        config.fixed_flavor = config_data.fixed_flavor
    else:
        config = SectionConfig(
            user_id=user_id,
            section_type=section_type,
            section_key=section_key,
            priority=config_data.priority,
            fixed_flavor=config_data.fixed_flavor
        )
        db.add(config)
    
    db.commit()
    db.refresh(config)
    return config

@router.delete("/{section_type}/{section_key}")
def delete_section_config(
    section_type: str,
    section_key: str,
    user_id: uuid.UUID = Depends(get_user_id),
    db: Session = Depends(get_db)
):
    """Delete section config (resets to default 'normal')."""
    db.query(SectionConfig).filter(
        SectionConfig.user_id == user_id,
        SectionConfig.section_type == section_type,
        SectionConfig.section_key == section_key
    ).delete()
    db.commit()
    return {"status": "deleted"}
