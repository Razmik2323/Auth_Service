from pydantic import BaseModel


class MockObject(BaseModel):
    """Fictional business object exposed by the mock endpoints."""

    id: int
    name: str
    owner: str
