from functools import lru_cache
from typing import Literal, Self

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_SECRET_KEY = "dev-insecure-secret-change-me-0000000000"
MIN_SECRET_BYTES = 32


class Settings(BaseSettings):
    """Application configuration loaded from the environment."""

    app_name: str = "auth-service"
    app_version: str = "0.1.0"
    app_env: Literal["dev", "test", "prod"] = "dev"
    app_debug: bool = False
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://auth:auth@db:5432/auth"
    db_pool_size: int = 20
    db_max_overflow: int = 10

    redis_url: str = "redis://redis:6379/0"

    secret_key: SecretStr = SecretStr(DEV_SECRET_KEY)
    jwt_algorithm: str = "HS256"
    access_token_ttl_seconds: int = 900
    refresh_token_ttl_seconds: int = 1209600

    rate_limit_enabled: bool = True
    rate_limit_default_max: int = 100
    rate_limit_default_window_seconds: int = 60
    rate_limit_auth_max: int = 10
    rate_limit_auth_window_seconds: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="after")
    def _validate_secret_key(self) -> Self:
        """Enforce a strong signing secret and forbid the default in production."""
        secret = self.secret_key.get_secret_value()
        if len(secret.encode("utf-8")) < MIN_SECRET_BYTES:
            raise ValueError(f"SECRET_KEY must be at least {MIN_SECRET_BYTES} bytes")
        if self.app_env == "prod" and secret == DEV_SECRET_KEY:
            raise ValueError("SECRET_KEY must be overridden in production")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
