from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Service health payload."""

    status: str
    env: str
    version: str
    db: str
    redis: str
