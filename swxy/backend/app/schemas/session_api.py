from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: str
    session_name: str
    created_at: datetime
    updated_at: datetime


class SessionListResponse(BaseModel):
    sessions: list[SessionResponse]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)


class CitationResponse(BaseModel):
    citation_id: int
    chunk_id: str
    document_id: str
    document_name: str
    content: str
    score: float | None = None
    positions: list[Any] = Field(default_factory=list)


class MessageResponse(BaseModel):
    message_id: str
    session_id: str
    user_question: str
    model_answer: str
    thinking: str | None
    citations: list[CitationResponse]
    recommendations: list[str]
    created_at: datetime


class TemporaryDocumentResponse(BaseModel):
    document_id: str
    document_name: str
    document_type: str
    file_size: int
    expires_in_seconds: int


class SessionDocumentsResponse(BaseModel):
    session_id: str
    has_document: bool
    document: TemporaryDocumentResponse | None = None

