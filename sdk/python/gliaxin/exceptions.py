class GliaxinError(Exception):
    """Base exception for all Gliaxin SDK errors."""
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class AuthError(GliaxinError):
    """Raised when the API key is missing or invalid (401)."""


class NotFoundError(GliaxinError):
    """Raised when the requested resource does not exist (404)."""


class ValidationError(GliaxinError):
    """Raised when a required field is missing or invalid (400)."""


class RateLimitError(GliaxinError):
    """Raised when burst or monthly limits are exceeded (429)."""


class ServerError(GliaxinError):
    """Raised on unexpected server errors (5xx)."""
