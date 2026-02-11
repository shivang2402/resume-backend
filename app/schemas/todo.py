from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class TodoCreate(BaseModel):
    text: str


class TodoUpdate(BaseModel):
    text: Optional[str] = None
    is_done: Optional[bool] = None
    position: Optional[int] = None


class TodoReorder(BaseModel):
    todo_ids: List[UUID]


class TodoResponse(BaseModel):
    id: UUID
    user_id: UUID
    text: str
    is_done: bool
    position: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
