class AppError(Exception):
    """Base application error carrying an HTTP status and machine code."""

    status_code: int = 400
    code: str = "error"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.code)
        self.message = message or self.code


class EmailAlreadyExistsError(AppError):
    """Raised when registering an email that already exists."""

    status_code = 409
    code = "email_already_exists"


class InvalidCredentialsError(AppError):
    """Raised when authentication fails for any reason."""

    status_code = 401
    code = "invalid_credentials"


class InvalidTokenError(AppError):
    """Raised when a token is missing, malformed, expired, or revoked."""

    status_code = 401
    code = "invalid_token"


class ForbiddenError(AppError):
    """Raised when the authenticated user lacks the required permission."""

    status_code = 403
    code = "forbidden"


class InvalidCurrentPasswordError(AppError):
    """Raised when the supplied current password does not match."""

    status_code = 400
    code = "invalid_current_password"


class NotFoundError(AppError):
    """Raised when a requested resource does not exist."""

    status_code = 404
    code = "not_found"


class ConflictError(AppError):
    """Raised when a resource conflicts with an existing one."""

    status_code = 409
    code = "conflict"
