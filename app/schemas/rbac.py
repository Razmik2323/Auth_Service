from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PermissionCreate(BaseModel):
    """Permission creation payload."""

    resource: str = Field(min_length=1, max_length=100)
    action: str = Field(min_length=1, max_length=50)
    description: str | None = Field(default=None, max_length=255)


class PermissionRead(BaseModel):
    """Public representation of a permission."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    resource: str
    action: str
    description: str | None


class RoleCreate(BaseModel):
    """Role creation payload."""

    name: str = Field(min_length=1, max_length=50)
    description: str | None = Field(default=None, max_length=255)


class RoleRead(BaseModel):
    """Public representation of a role with its permissions."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    permissions: list[PermissionRead]


class AssignPermissionRequest(BaseModel):
    """Payload assigning a permission to a role."""

    permission_id: UUID


class AssignRoleRequest(BaseModel):
    """Payload assigning a role to a user."""

    role_id: UUID
