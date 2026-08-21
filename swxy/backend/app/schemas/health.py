from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    postgresql: bool
    elasticsearch: bool
    redis: bool
    model_provider: str
    model_configured: bool
