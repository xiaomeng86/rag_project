from fastapi import APIRouter, Depends, File, HTTPException, Security, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from config import MAX_UPLOAD_BYTES
from models.message import Message
from schemas.session_api import (
    MessageResponse,
    SessionDocumentsResponse,
    SessionListResponse,
    SessionResponse,
    TemporaryDocumentResponse,
)
from service.auth import access_security, credential_user_id
from service.session_service import create_session, list_sessions, require_session
from service.temporary_document_service import get_temporary_document, store_temporary_document
from utils.database import get_db


router = APIRouter(prefix="/sessions", tags=["会话"])


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def new_session(
    credentials: HTTPAuthorizationCredentials = Security(access_security),
    db: Session = Depends(get_db),
):
    return create_session(db, credential_user_id(credentials))


@router.get("", response_model=SessionListResponse)
def get_sessions(
    credentials: HTTPAuthorizationCredentials = Security(access_security),
    db: Session = Depends(get_db),
):
    return SessionListResponse(sessions=list_sessions(db, credential_user_id(credentials)))


@router.get("/{session_id}/messages", response_model=list[MessageResponse])
def get_messages(
    session_id: str,
    credentials: HTTPAuthorizationCredentials = Security(access_security),
    db: Session = Depends(get_db),
):
    require_session(db, session_id, credential_user_id(credentials))
    return (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
        .all()
    )


@router.put("/{session_id}/temporary-document", response_model=TemporaryDocumentResponse)
async def put_temporary_document(
    session_id: str,
    file: UploadFile = File(...),
    credentials: HTTPAuthorizationCredentials = Security(access_security),
    db: Session = Depends(get_db),
):
    require_session(db, session_id, credential_user_id(credentials))
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if not content:
        raise HTTPException(status_code=400, detail="文件内容为空")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="临时文档不能超过 5 MB")
    try:
        return store_temporary_document(session_id, file.filename or "", content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{session_id}/documents", response_model=SessionDocumentsResponse)
def get_session_document(
    session_id: str,
    credentials: HTTPAuthorizationCredentials = Security(access_security),
    db: Session = Depends(get_db),
):
    require_session(db, session_id, credential_user_id(credentials))
    document = get_temporary_document(session_id)
    if document:
        document = {key: value for key, value in document.items() if key != "content"}
    return SessionDocumentsResponse(
        session_id=session_id,
        has_document=document is not None,
        document=document,
    )
