"""Permanent-document parsing, embedding and Elasticsearch ingestion."""

from __future__ import annotations

import datetime as dt
import hashlib
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from service.core.rag.app.naive import chunk
from service.core.rag.nlp.model import generate_embedding
from service.core.rag.utils.es_conn import ESConnection


EMBEDDING_DIMENSIONS = 1024
PDF_TEXT_LAYER_SAMPLE_PAGES = 3
PDF_TEXT_LAYER_MIN_CHARACTERS = 24


def _progress(_progress=None, _message="", **_kwargs) -> None:
    return None


def _pdf_has_usable_text_layer(file_path: str | Path) -> bool:
    """Use native extraction for searchable PDFs and reserve DeepDoc for scans."""
    try:
        reader = PdfReader(str(file_path))
        sample = "".join(
            page.extract_text() or ""
            for page in reader.pages[:PDF_TEXT_LAYER_SAMPLE_PAGES]
        )
    except Exception:
        return False
    return len("".join(sample.split())) >= PDF_TEXT_LAYER_MIN_CHARACTERS


def parse(file_path: str | Path) -> list[dict[str, Any]]:
    """Route supported files; scanned PDFs retain the DeepDoc OCR/layout path."""
    path = Path(file_path)
    if path.suffix.lower() == ".pdf":
        layout_mode = (
            "Plain Text" if _pdf_has_usable_text_layer(path) else "DeepDOC"
        )
        return chunk(
            str(path),
            callback=_progress,
            parser_config={
                "chunk_token_num": 128,
                "delimiter": "\n!?。；！？",
                "layout_recognize": layout_mode,
            },
        )
    return chunk(str(path), callback=_progress)


def batch_generate_embeddings(texts: list[str]) -> list[list[float]]:
    embeddings = generate_embedding(texts, dimensions=EMBEDDING_DIMENSIONS)
    if len(embeddings) != len(texts):
        raise RuntimeError("Embedding 返回数量与 Chunk 数量不一致")
    if any(len(vector) != EMBEDDING_DIMENSIONS for vector in embeddings):
        raise RuntimeError("Embedding 维度不是 1024")
    return embeddings


def process_items(
    items: list[dict[str, Any]],
    file_name: str,
    document_id: str,
) -> list[dict[str, Any]]:
    texts = [str(item.get("content_with_weight", "")).strip() for item in items]
    if not texts or any(not text for text in texts):
        raise RuntimeError("文档解析产生了空 Chunk")
    embeddings = batch_generate_embeddings(texts)
    now = dt.datetime.now(dt.timezone.utc)
    documents: list[dict[str, Any]] = []
    for ordinal, (item, embedding) in enumerate(zip(items, embeddings), start=1):
        content = texts[ordinal - 1]
        chunk_id = hashlib.sha256(
            f"{document_id}:{ordinal}:{content}".encode("utf-8")
        ).hexdigest()[:32]
        document = {
            "id": chunk_id,
            "content_ltks": item.get("content_ltks", ""),
            "content_with_weight": content,
            "content_sm_ltks": item.get("content_sm_ltks", ""),
            "important_kwd": [],
            "important_tks": [],
            "question_kwd": [],
            "question_tks": [],
            "create_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "create_timestamp_flt": now.timestamp(),
            "available_int": 1,
            "kb_id": document_id,
            "doc_id": document_id,
            "docnm_kwd": Path(file_name).name,
            "docnm": Path(file_name).name,
            "title_tks": item.get("title_tks", ""),
            "q_1024_vec": embedding,
        }
        for field in ("page_num_int", "position_int", "top_int"):
            if item.get(field) is not None:
                document[field] = item[field]
        documents.append(document)
    return documents


def execute_insert_process(
    file_path: str | Path,
    file_name: str,
    user_id: int | str,
    document_id: str,
) -> int:
    """Parse, embed and propagate every Elasticsearch Bulk failure."""
    parsed_documents = parse(file_path)
    if not parsed_documents:
        raise RuntimeError("文档解析结果为空")
    processed_documents = process_items(parsed_documents, file_name, document_id)
    connection = ESConnection()
    inserted_ids = connection.insert(
        processed_documents, connection.index_name(user_id)
    )
    if len(inserted_ids) != len(processed_documents):
        raise RuntimeError("Elasticsearch 未完整写入所有 Chunk")
    return len(inserted_ids)
