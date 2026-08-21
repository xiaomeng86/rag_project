from fastapi import APIRouter, Depends, File, HTTPException, Security, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from config import MAX_UPLOAD_BYTES
from schemas.knowledge import DeleteDocumentResponse, KnowledgeDocumentResponse
from service.auth import access_security, credential_user_id
from service.knowledge_service import create_document, delete_document, list_documents
from utils.database import get_db


router = APIRouter(prefix="/knowledge", tags=["知识库"])


@router.get("/documents", response_model=list[KnowledgeDocumentResponse])
def get_documents(
    credentials: HTTPAuthorizationCredentials = Security(access_security),
    db: Session = Depends(get_db),
):
    return list_documents(db, credential_user_id(credentials))


@router.post(
    "/documents",
    response_model=KnowledgeDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(...),
    credentials: HTTPAuthorizationCredentials = Security(access_security),
    db: Session = Depends(get_db),
):
    try:
        content = await file.read(MAX_UPLOAD_BYTES + 1)
        return create_document(
            db,
            credential_user_id(credentials),
            file.filename or "",
            content,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/documents/{document_id}", response_model=DeleteDocumentResponse)
def remove_document(
    document_id: str,
    credentials: HTTPAuthorizationCredentials = Security(access_security),
    db: Session = Depends(get_db),
):
    try:
        deleted_chunks = delete_document(
            db, credential_user_id(credentials), document_id
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return DeleteDocumentResponse(
        document_id=document_id,
        deleted_chunks=deleted_chunks,
        message="文档已删除",
    )
