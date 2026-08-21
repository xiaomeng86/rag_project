from datetime import datetime

from pydantic import BaseModel, ConfigDict


class KnowledgeDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: str
    file_name: str
    document_type: str
    file_size: int
    status: str
    chunk_count: int
    created_at: datetime
    updated_at: datetime


class DeleteDocumentResponse(BaseModel):
    document_id: str
    deleted_chunks: int
    message: str

