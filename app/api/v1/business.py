from fastapi import APIRouter, Depends, status

from app.api.deps import require_permission
from app.schemas.business import MockObject

router = APIRouter(tags=["business"])

_DOCUMENTS = [
    MockObject(id=1, name="Quarterly report", owner="alice"),
    MockObject(id=2, name="Design proposal", owner="bob"),
]
_REPORTS = [MockObject(id=10, name="Sales summary", owner="carol")]
_PROJECTS = [MockObject(id=100, name="Migration", owner="dave")]


@router.get(
    "/documents",
    response_model=list[MockObject],
    dependencies=[Depends(require_permission("documents", "read"))],
)
async def list_documents() -> list[MockObject]:
    """Return the mock documents visible to authorized users."""
    return _DOCUMENTS


@router.post(
    "/documents",
    response_model=MockObject,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("documents", "create"))],
)
async def create_document() -> MockObject:
    """Return a mock document representing a created resource."""
    return MockObject(id=3, name="New document", owner="you")


@router.get(
    "/reports",
    response_model=list[MockObject],
    dependencies=[Depends(require_permission("reports", "read"))],
)
async def list_reports() -> list[MockObject]:
    """Return the mock reports visible to authorized users."""
    return _REPORTS


@router.get(
    "/projects",
    response_model=list[MockObject],
    dependencies=[Depends(require_permission("projects", "read"))],
)
async def list_projects() -> list[MockObject]:
    """Return the mock projects visible to authorized users."""
    return _PROJECTS
