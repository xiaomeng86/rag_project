"""Permanent knowledge-base document lifecycle with compensating cleanup."""

from __future__ import annotations

import logging
from pathlib import Path
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from config import MAX_UPLOAD_BYTES, SUPPORTED_KNOWLEDGE_EXTENSIONS, UPLOAD_DIR
from models.knowledgebase import KnowledgeDocument
from service.core.file_parse import execute_insert_process
from service.core.rag.utils.es_conn import ESConnection


logger = logging.getLogger(__name__)


def _safe_file_name(file_name: str) -> str:
    if not file_name or "\x00" in file_name or "/" in file_name or "\\" in file_name:
        raise ValueError("文件名不合法")
    safe_name = Path(file_name).name
    if safe_name in {"", ".", ".."}:
        raise ValueError("文件名不合法")
    if Path(safe_name).suffix.lower() not in SUPPORTED_KNOWLEDGE_EXTENSIONS:
        raise ValueError("仅支持 PDF、DOCX、XLSX、TXT、Markdown 和 HTML")
    return safe_name


def _validate_content(content: bytes) -> None:
    if not content:
        raise ValueError("文件内容为空")
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError("文件不能超过 5 MB")


def list_documents(db: Session, user_id: int) -> list[KnowledgeDocument]:
    return (
        db.query(KnowledgeDocument)
        .filter(KnowledgeDocument.user_id == user_id)
        .order_by(KnowledgeDocument.created_at.desc())
        .all()
    )


def require_document(db: Session, user_id: int, document_id: str) -> KnowledgeDocument:
    document = (
        db.query(KnowledgeDocument)
        .filter(
            KnowledgeDocument.document_id == document_id,
            KnowledgeDocument.user_id == user_id,
        )
        .first()
    )
    if not document:
        raise LookupError("文档不存在")
    return document


def create_document(
    db: Session,
    user_id: int,
    file_name: str,
    content: bytes,
) -> KnowledgeDocument:
    safe_name = _safe_file_name(file_name)
    _validate_content(content)
    document_id = uuid.uuid4().hex
    document_dir = UPLOAD_DIR / str(user_id) / document_id
    storage_path = document_dir / safe_name
    document = KnowledgeDocument(
        document_id=document_id,
        user_id=user_id,
        file_name=safe_name,
        document_type=Path(safe_name).suffix.lower().removeprefix("."),
        file_size=len(content),
        storage_path=str(storage_path),
        status="processing",
        chunk_count=0,
    )
    db.add(document)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("同名文档已存在") from exc

    try:
        document_dir.mkdir(parents=True, exist_ok=False)
        storage_path.write_bytes(content)
        if storage_path.stat().st_size != len(content):
            raise RuntimeError("文件落盘大小不一致")
        document.chunk_count = execute_insert_process(
            storage_path, safe_name, user_id, document_id
        )
        document.status = "ready"
        db.commit()
        db.refresh(document)
        return document
    except Exception:
        db.rollback()
        cleanup_errors: list[str] = []
        try:
            connection = ESConnection()
            connection.delete_by_document(connection.index_name(user_id), document_id)
        except Exception as cleanup_error:  # cleanup is still attempted for all resources
            cleanup_errors.append(f"ES: {cleanup_error}")
        try:
            storage_path.unlink(missing_ok=True)
            document_dir.rmdir()
        except OSError as cleanup_error:
            cleanup_errors.append(f"磁盘: {cleanup_error}")
        try:
            (UPLOAD_DIR / str(user_id)).rmdir()
        except OSError:
            pass
        try:
            db.query(KnowledgeDocument).filter(
                KnowledgeDocument.document_id == document_id
            ).delete(synchronize_session=False)
            db.commit()
        except Exception as cleanup_error:
            db.rollback()
            cleanup_errors.append(f"PostgreSQL: {cleanup_error}")
        if cleanup_errors:
            logger.error("文档入库补偿清理未完全成功: %s", "; ".join(cleanup_errors))
        raise


def delete_document(db: Session, user_id: int, document_id: str) -> int:
    document = require_document(db, user_id, document_id)
    connection = ESConnection()
    deleted_chunks = connection.delete_by_document(
        connection.index_name(user_id), document_id
    )
    storage_path = Path(document.storage_path)
    storage_path.unlink(missing_ok=True)
    try:
        storage_path.parent.rmdir()
        (UPLOAD_DIR / str(user_id)).rmdir()
    except OSError:
        pass
    db.delete(document)
    db.commit()
    return deleted_chunks
