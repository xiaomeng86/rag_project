from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from config import DASHSCOPE_API_KEY, MODEL_PROVIDER
from schemas.health import HealthResponse
from service.core.rag.utils.es_conn import ESConnection
from service.temporary_document_service import redis_health
from utils.database import get_db


router = APIRouter(tags=["运维"])


@router.get("/health", response_model=HealthResponse)
def health(response: Response, db: Session = Depends(get_db)):
    postgresql = elasticsearch = redis = False
    try:
        db.execute(text("SELECT 1"))
        postgresql = True
    except Exception:
        pass
    try:
        elasticsearch = ESConnection().health()
    except Exception:
        pass
    try:
        redis = redis_health()
    except Exception:
        pass
    model_configured = MODEL_PROVIDER == "mock" or bool(DASHSCOPE_API_KEY)
    healthy = postgresql and elasticsearch and redis and model_configured
    if not healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(
        status="ok" if healthy else "unavailable",
        postgresql=postgresql,
        elasticsearch=elasticsearch,
        redis=redis,
        model_provider=MODEL_PROVIDER,
        model_configured=model_configured,
    )
