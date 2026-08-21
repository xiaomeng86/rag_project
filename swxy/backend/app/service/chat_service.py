"""Owned-session RAG chat orchestration and SSE persistence."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone

from models.knowledgebase import KnowledgeDocument
from models.message import Message
from service.core.retrieval import retrieve_content
from service.model_provider import recommended_questions, session_name, stream_answer
from service.session_service import require_session
from service.temporary_document_service import get_temporary_document
from utils.database import SessionLocal


def _sse(event_type: str, **payload) -> str:
    data = {"type": event_type, **payload}
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]", text.lower()))


def _temporary_references(session_id: str, question: str) -> list[dict]:
    document = get_temporary_document(session_id)
    if not document:
        return []
    text = str(document.get("content", ""))
    chunks = [text[start : start + 2000] for start in range(0, len(text), 2000)]
    query_tokens = _tokens(question)
    ranked: list[tuple[float, int, str]] = []
    for index, chunk in enumerate(chunks):
        chunk_tokens = _tokens(chunk)
        score = len(query_tokens & chunk_tokens) / (len(query_tokens) or 1)
        ranked.append((score, index, chunk))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [
        {
            "chunk_id": f"temporary-{session_id}-{index + 1}",
            "document_id": str(document["document_id"]),
            "document_name": str(document["document_name"]),
            "content": chunk,
            "score": score,
            "positions": [],
        }
        for score, index, chunk in ranked[:2]
    ]


def _number_citations(references: list[dict]) -> list[dict]:
    return [
        {
            "citation_id": index,
            "chunk_id": reference["chunk_id"],
            "document_id": reference["document_id"],
            "document_name": reference["document_name"],
            "content": reference["content"],
            "score": reference.get("score"),
            "positions": reference.get("positions", []),
        }
        for index, reference in enumerate(references, start=1)
    ]


def build_prompt(question: str, citations: list[dict]) -> str:
    evidence = "\n\n".join(
        (
            f"[{item['citation_id']}] chunk_id={item['chunk_id']}; "
            f"document_id={item['document_id']}; document_name={item['document_name']}\n"
            f"{item['content']}"
        )
        for item in citations
    ) or "（无可用证据）"
    return (
        "你是企业知识库助手。只能根据编号证据回答；无证据时明确说无法确认。\n"
        "引用时在对应句末使用 ##编号$$，编号必须与下方证据一致，不得编造来源。\n\n"
        f"证据：\n{evidence}\n\n用户问题：{question}"
    )


def stream_chat(session_id: str, user_id: int, question: str):
    db = SessionLocal()
    try:
        session = require_session(db, session_id, user_id)
        document_ids = [
            row.document_id
            for row in db.query(KnowledgeDocument.document_id).filter(
                KnowledgeDocument.user_id == user_id,
                KnowledgeDocument.status == "ready",
            )
        ]
        permanent = retrieve_content(user_id, question, document_ids)
        temporary = _temporary_references(session_id, question)
        references = (temporary[:2] + permanent[:3]) if temporary else permanent[:5]
        citations = _number_citations(references)
        prompt = build_prompt(question, citations)
        yield _sse("citations", citations=citations)

        thinking_parts: list[str] = []
        answer_parts: list[str] = []
        for event_type, content in stream_answer(prompt, question, citations):
            if event_type == "thinking":
                thinking_parts.append(content)
                yield _sse("thinking", content=content)
            elif event_type == "answer":
                answer_parts.append(content)
                yield _sse("answer", content=content)

        recommendations = recommended_questions(question)
        yield _sse("recommendations", recommendations=recommendations)
        message = Message(
            message_id=str(uuid.uuid4()),
            session_id=session_id,
            user_question=question,
            model_answer="".join(answer_parts),
            thinking="".join(thinking_parts) or None,
            citations=citations,
            recommendations=recommendations,
        )
        db.add(message)
        if session.session_name == "新对话":
            session.session_name = session_name(question)
        session.updated_at = datetime.now(timezone.utc)
        db.commit()
        yield _sse("done", message_id=message.message_id)
    except Exception:
        db.rollback()
        yield _sse("error", message="问答处理失败")
    finally:
        db.close()
