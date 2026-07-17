from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class UserRead(BaseModel):
    """Public representation of a user."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    first_name: str
    last_name: str
    middle_name: str | None
    email: EmailStr
    is_active: bool
    created_at: datetime


class UserUpdate(BaseModel):
    """Partial profile update payload."""

    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)


class ChangePasswordRequest(BaseModel):
    """Password change payload."""

    current_password: str
    new_password: str = Field(min_length=12, max_length=128)
    new_password_repeat: str

    @model_validator(mode="after")
    def _passwords_match(self) -> Self:
        """Ensure both new-password fields are identical."""
        if self.new_password != self.new_password_repeat:
            raise ValueError("passwords do not match")
        return self
