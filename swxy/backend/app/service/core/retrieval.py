"""Hybrid keyword/vector retrieval followed by DashScope-compatible reranking."""

from __future__ import annotations

from pathlib import Path

from service.core.rag.nlp.search_v2 import Dealer
from service.core.rag.utils.es_conn import ESConnection


def retrieve_content(
    user_id: int | str,
    question: str,
    document_ids: list[str],
) -> list[dict]:
    if not document_ids:
        return []
    dealer = Dealer(dataStore=ESConnection())
    result = dealer.retrieval(
        question=question,
        tenant_ids=[str(user_id)],
        kb_ids=document_ids,
        page=1,
        page_size=5,
        similarity_threshold=0.1,
        vector_similarity_weight=0.6,
        top=1024,
    )
    references: list[dict] = []
    for chunk in result.get("chunks", []):
        references.append(
            {
                "chunk_id": str(chunk.get("chunk_id", "")),
                "document_id": str(chunk.get("doc_id", "")),
                "document_name": Path(str(chunk.get("docnm_kwd", ""))).name,
                "content": str(chunk.get("content_with_weight", "")),
                "score": float(chunk.get("similarity", 0.0)),
                "positions": chunk.get("positions", []),
            }
        )
    return references
