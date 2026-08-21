from __future__ import annotations

from pathlib import Path

import pytest

from models.knowledgebase import KnowledgeDocument
from models.user import User
from service import knowledge_service
from utils.database import SessionLocal
from tests.conftest import token_for


def test_session_is_persisted_immediately(client, auth_headers):
    created = client.post("/api/v1/sessions", headers=auth_headers)
    assert created.status_code == 201
    sessions = client.get("/api/v1/sessions", headers=auth_headers)
    assert sessions.status_code == 200
    assert [item["session_id"] for item in sessions.json()["sessions"]] == [
        created.json()["session_id"]
    ]


def test_session_history_and_document_endpoints_enforce_owner(client):
    alice = {"Authorization": f"Bearer {token_for(client, 'alice-owner')}"}
    bob = {"Authorization": f"Bearer {token_for(client, 'bob-owner')}"}
    session_id = client.post("/api/v1/sessions", headers=alice).json()["session_id"]

    assert client.get(f"/api/v1/sessions/{session_id}/messages", headers=bob).status_code == 404
    assert client.get(f"/api/v1/sessions/{session_id}/documents", headers=bob).status_code == 404
    assert (
        client.put(
            f"/api/v1/sessions/{session_id}/temporary-document",
            headers=bob,
            files={"file": ("private.txt", b"private", "text/plain")},
        ).status_code
        == 404
    )


def test_knowledge_and_chat_endpoints_enforce_owner(client, tmp_path: Path):
    alice = {"Authorization": f"Bearer {token_for(client, 'alice-knowledge')}"}
    bob = {"Authorization": f"Bearer {token_for(client, 'bob-knowledge')}"}
    session_id = client.post("/api/v1/sessions", headers=alice).json()["session_id"]

    db = SessionLocal()
    owner = db.query(User).filter(User.username == "alice-knowledge").one()
    db.add(
        KnowledgeDocument(
            document_id="owned-document",
            user_id=owner.id,
            file_name="owned.txt",
            document_type="txt",
            file_size=5,
            storage_path=str(tmp_path / "owned.txt"),
            status="ready",
            chunk_count=1,
        )
    )
    db.commit()
    db.close()

    assert client.get("/api/v1/knowledge/documents", headers=bob).json() == []
    assert (
        client.delete(
            "/api/v1/knowledge/documents/owned-document", headers=bob
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/sessions/{session_id}/chat",
            headers=bob,
            json={"message": "private question"},
        ).status_code
        == 404
    )


def test_failed_ingestion_compensates_disk_es_and_postgresql(monkeypatch, tmp_path: Path):
    db = SessionLocal()
    user = User(username="transaction-user", password_hash="unused")
    db.add(user)
    db.commit()
    db.refresh(user)

    deleted = []

    class FakeConnection:
        @staticmethod
        def index_name(user_id):
            return f"gsk-user-{user_id}"

        def delete_by_document(self, index_name, document_id):
            deleted.append((index_name, document_id))
            return 2

    monkeypatch.setattr(knowledge_service, "UPLOAD_DIR", tmp_path / "uploads")
    monkeypatch.setattr(knowledge_service, "ESConnection", FakeConnection)
    monkeypatch.setattr(
        knowledge_service,
        "execute_insert_process",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("bulk failed")),
    )

    with pytest.raises(RuntimeError, match="bulk failed"):
        knowledge_service.create_document(
            db, user.id, "transaction.txt", b"synthetic transaction content"
        )

    assert db.query(KnowledgeDocument).count() == 0
    assert not (tmp_path / "uploads").exists() or not any((tmp_path / "uploads").rglob("*"))
    assert len(deleted) == 1
    db.close()
