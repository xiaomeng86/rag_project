from fastapi import APIRouter, Depends, Security
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from schemas.session_api import ChatRequest
from service.auth import access_security, credential_user_id
from service.chat_service import stream_chat
from service.session_service import require_session
from utils.database import get_db


router = APIRouter(prefix="/sessions", tags=["问答"])


@router.post("/{session_id}/chat")
def chat(
    session_id: str,
    request: ChatRequest,
    credentials: HTTPAuthorizationCredentials = Security(access_security),
    db: Session = Depends(get_db),
):
    user_id = credential_user_id(credentials)
    require_session(db, session_id, user_id)
    return StreamingResponse(
        stream_chat(session_id, user_id, request.message.strip()),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
