from sqlalchemy.orm import Session
from sqlalchemy import and_
from uuid import UUID
from typing import Optional

from app.models.section import Section
from app.schemas.section import SectionCreate, SectionUpdate


def get_next_version(current_version: str) -> str:
    """1.0 -> 1.1, 1.9 -> 1.10"""
    major, minor = current_version.split(".")
    return f"{major}.{int(minor) + 1}"


def get_all_sections(db: Session, user_id: UUID) -> list[Section]:
    return db.query(Section).filter(Section.user_id == user_id).all()


def get_sections_by_type(db: Session, user_id: UUID, type: str) -> list[Section]:
    return db.query(Section).filter(
        and_(Section.user_id == user_id, Section.type == type)
    ).all()


def get_section_versions(
    db: Session, user_id: UUID, type: str, key: str, flavor: str
) -> list[Section]:
    return db.query(Section).filter(
        and_(
            Section.user_id == user_id,
            Section.type == type,
            Section.key == key,
            Section.flavor == flavor,
        )
    ).order_by(Section.created_at.desc()).all()


def get_section_by_version(
    db: Session, user_id: UUID, type: str, key: str, flavor: str, version: str
) -> Optional[Section]:
    return db.query(Section).filter(
        and_(
            Section.user_id == user_id,
            Section.type == type,
            Section.key == key,
            Section.flavor == flavor,
            Section.version == version,
        )
    ).first()


def get_current_section(
    db: Session, user_id: UUID, type: str, key: str, flavor: str
) -> Optional[Section]:
    return db.query(Section).filter(
        and_(
            Section.user_id == user_id,
            Section.type == type,
            Section.key == key,
            Section.flavor == flavor,
            Section.is_current == True,
        )
    ).first()


def create_section(db: Session, user_id: UUID, section: SectionCreate) -> Section:
    db_section = Section(
        user_id=user_id,
        type=section.type,
        key=section.key,
        flavor=section.flavor,
        version="1.0",
        content=section.content,
        is_current=True,
    )
    db.add(db_section)
    db.commit()
    db.refresh(db_section)
    return db_section


def update_section(
    db: Session, user_id: UUID, type: str, key: str, flavor: str, section: SectionUpdate
) -> Optional[Section]:
    # Get current version
    current = get_current_section(db, user_id, type, key, flavor)
    if not current:
        return None

    # Mark old as not current
    current.is_current = False

    # Create new version
    new_version = get_next_version(current.version)
    new_section = Section(
        user_id=user_id,
        type=type,
        key=key,
        flavor=flavor,
        version=new_version,
        content=section.content,
        is_current=True,
    )
    db.add(new_section)
    db.commit()
    db.refresh(new_section)
    return new_section


def delete_section_version(
    db: Session, user_id: UUID, type: str, key: str, flavor: str, version: str
) -> bool:
    section = get_section_by_version(db, user_id, type, key, flavor, version)
    if not section:
        return False

    was_current = section.is_current
    db.delete(section)

    # If deleted was current, make the latest remaining version current
    if was_current:
        latest = db.query(Section).filter(
            and_(
                Section.user_id == user_id,
                Section.type == type,
                Section.key == key,
                Section.flavor == flavor,
            )
        ).order_by(Section.created_at.desc()).first()
        if latest:
            latest.is_current = True

    db.commit()
    return True