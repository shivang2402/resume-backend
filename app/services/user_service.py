from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional

from app.models.user import User
from app.schemas.user import UserCreate


def get_user_by_id(db: Session, user_id: UUID) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def get_user_by_provider(db: Session, provider: str, provider_id: str) -> Optional[User]:
    return db.query(User).filter(
        User.provider == provider,
        User.provider_id == provider_id
    ).first()


def create_user(db: Session, user: UserCreate) -> User:
    db_user = User(
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        provider=user.provider,
        provider_id=user.provider_id,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def sync_user(db: Session, user: UserCreate) -> User:
    """Create user if not exists, or update if exists."""
    existing = get_user_by_provider(db, user.provider, user.provider_id)
    
    if existing:
        # Update existing user
        existing.email = user.email
        existing.name = user.name
        existing.avatar_url = user.avatar_url
        db.commit()
        db.refresh(existing)
        return existing
    
    # Create new user
    return create_user(db, user)