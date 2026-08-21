from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models.session import ChatSession


def create_session(db: Session, user_id: int) -> ChatSession:
    session = ChatSession(
        session_id=uuid.uuid4().hex[:16],
        user_id=user_id,
        session_name="新对话",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def require_session(db: Session, session_id: str, user_id: int) -> ChatSession:
    session = (
        db.query(ChatSession)
        .filter(ChatSession.session_id == session_id, ChatSession.user_id == user_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    return session


def list_sessions(db: Session, user_id: int) -> list[ChatSession]:
    return (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user_id)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )

