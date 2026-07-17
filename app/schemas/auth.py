from typing import Self

from pydantic import BaseModel, EmailStr, Field, model_validator


class RegisterRequest(BaseModel):
    """Registration payload."""

    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    password_repeat: str

    @model_validator(mode="after")
    def _passwords_match(self) -> Self:
        """Ensure both password fields are identical."""
        if self.password != self.password_repeat:
            raise ValueError("passwords do not match")
        return self


class LoginRequest(BaseModel):
    """Login payload."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Issued access and refresh token pair."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    """Refresh payload."""

    refresh_token: str


class LogoutRequest(BaseModel):
    """Logout payload."""

    refresh_token: str
