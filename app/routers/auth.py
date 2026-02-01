from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional

from app.database import get_db
from app.schemas.user import UserCreate, UserResponse
from app.services import user_service

router = APIRouter()


@router.post("/sync")
def sync_user(
    user: UserCreate,
    db: Session = Depends(get_db),
):
    """
    Sync user from NextAuth OAuth callback.
    Creates user if not exists, updates if exists.
    """
    synced_user = user_service.sync_user(db, user)
    return UserResponse.model_validate(synced_user)


@router.get("/me")
def get_current_user(
    x_user_id: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Get current user by ID from header.
    In production, this would validate a JWT token.
    """
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        user_id = UUID(x_user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    user = user_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse.model_validate(user)