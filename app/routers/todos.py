from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.database import get_db
from app.models.todo import Todo
from app.schemas.todo import TodoCreate, TodoUpdate, TodoReorder, TodoResponse

router = APIRouter()


def get_current_user_id(x_user_id: str = Header(...)) -> UUID:
    return UUID(x_user_id)


@router.get("", response_model=List[TodoResponse])
def list_todos(
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    todos = (
        db.query(Todo)
        .filter(Todo.user_id == user_id)
        .order_by(Todo.position.asc(), Todo.created_at.desc())
        .all()
    )
    return [TodoResponse.model_validate(t) for t in todos]


@router.post("", response_model=TodoResponse, status_code=201)
def create_todo(
    todo: TodoCreate,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    # Get max position
    max_pos = db.query(Todo).filter(Todo.user_id == user_id).count()

    new_todo = Todo(
        user_id=user_id,
        text=todo.text,
        is_done=False,
        position=max_pos,
    )
    db.add(new_todo)
    db.commit()
    db.refresh(new_todo)
    return TodoResponse.model_validate(new_todo)


@router.put("/{todo_id}", response_model=TodoResponse)
def update_todo(
    todo_id: UUID,
    todo: TodoUpdate,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    existing = db.query(Todo).filter(Todo.id == todo_id, Todo.user_id == user_id).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Todo not found")

    if todo.text is not None:
        existing.text = todo.text
    if todo.is_done is not None:
        existing.is_done = todo.is_done
    if todo.position is not None:
        existing.position = todo.position

    db.commit()
    db.refresh(existing)
    return TodoResponse.model_validate(existing)


@router.delete("/{todo_id}", status_code=204)
def delete_todo(
    todo_id: UUID,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    existing = db.query(Todo).filter(Todo.id == todo_id, Todo.user_id == user_id).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Todo not found")

    db.delete(existing)
    db.commit()
    return None


@router.put("/reorder/bulk", response_model=List[TodoResponse])
def reorder_todos(
    reorder: TodoReorder,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    todos = db.query(Todo).filter(Todo.user_id == user_id).all()
    todo_map = {t.id: t for t in todos}

    for idx, todo_id in enumerate(reorder.todo_ids):
        if todo_id in todo_map:
            todo_map[todo_id].position = idx

    db.commit()

    updated = (
        db.query(Todo)
        .filter(Todo.user_id == user_id)
        .order_by(Todo.position.asc())
        .all()
    )
    return [TodoResponse.model_validate(t) for t in updated]


@router.delete("/completed/clear", status_code=204)
def clear_completed(
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    db.query(Todo).filter(Todo.user_id == user_id, Todo.is_done == True).delete()
    db.commit()
    return None
