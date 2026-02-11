from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.database import get_db
from app.models.resume_preset import ResumePreset
from app.schemas.resume_preset import ResumePresetCreate, ResumePresetUpdate, ResumePresetResponse

router = APIRouter()


def get_current_user_id(x_user_id: str = Header(...)) -> UUID:
    return UUID(x_user_id)


@router.get("", response_model=List[ResumePresetResponse])
def list_presets(
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    presets = (
        db.query(ResumePreset)
        .filter(ResumePreset.user_id == user_id)
        .order_by(ResumePreset.updated_at.desc())
        .all()
    )
    return [ResumePresetResponse.model_validate(p) for p in presets]


@router.post("", response_model=ResumePresetResponse, status_code=201)
def create_preset(
    preset: ResumePresetCreate,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    new_preset = ResumePreset(
        user_id=user_id,
        name=preset.name,
        resume_config=preset.resume_config,
    )
    db.add(new_preset)
    db.commit()
    db.refresh(new_preset)
    return ResumePresetResponse.model_validate(new_preset)


@router.get("/{preset_id}", response_model=ResumePresetResponse)
def get_preset(
    preset_id: UUID,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    preset = db.query(ResumePreset).filter(
        ResumePreset.id == preset_id, ResumePreset.user_id == user_id
    ).first()
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    return ResumePresetResponse.model_validate(preset)


@router.put("/{preset_id}", response_model=ResumePresetResponse)
def update_preset(
    preset_id: UUID,
    preset: ResumePresetUpdate,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    existing = db.query(ResumePreset).filter(
        ResumePreset.id == preset_id, ResumePreset.user_id == user_id
    ).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Preset not found")

    if preset.name is not None:
        existing.name = preset.name
    if preset.resume_config is not None:
        existing.resume_config = preset.resume_config

    db.commit()
    db.refresh(existing)
    return ResumePresetResponse.model_validate(existing)


@router.delete("/{preset_id}", status_code=204)
def delete_preset(
    preset_id: UUID,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    existing = db.query(ResumePreset).filter(
        ResumePreset.id == preset_id, ResumePreset.user_id == user_id
    ).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Preset not found")

    db.delete(existing)
    db.commit()
    return None
