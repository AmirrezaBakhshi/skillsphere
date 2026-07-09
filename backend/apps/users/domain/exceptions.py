class UserAlreadyExistsError(Exception):
    """Raised when registering an email/username that's already taken."""


class InvalidCredentialsError(Exception):
    """Raised when a login attempt doesn't match any active user."""


class UserNotFoundError(Exception):
    """Raised when a lookup by id/email finds nothing."""
