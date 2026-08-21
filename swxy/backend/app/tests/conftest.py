from __future__ import annotations

import os
from pathlib import Path
import tempfile

import pytest


test_root = Path(tempfile.gettempdir()) / "gsk-poc-pytest"
test_root.mkdir(parents=True, exist_ok=True)
database_path = test_root / "app.db"
database_path.unlink(missing_ok=True)

os.environ["MODEL_PROVIDER"] = "mock"
os.environ["DATABASE_URL"] = f"sqlite:///{database_path.as_posix()}"
os.environ["UPLOAD_DIR"] = str(test_root / "uploads")
os.environ["JWT_SECRET_KEY"] = "pytest-secret-key"

from fastapi.testclient import TestClient

from app_main import app
from models import Base
from utils.database import engine


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as value:
        yield value


def token_for(client: TestClient, username: str) -> str:
    credentials = {"username": username, "password": "password123"}
    response = client.post("/api/v1/auth/register", json=credentials)
    assert response.status_code == 201
    response = client.post("/api/v1/auth/login", json=credentials)
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    return {"Authorization": f"Bearer {token_for(client, 'alice')}"}
