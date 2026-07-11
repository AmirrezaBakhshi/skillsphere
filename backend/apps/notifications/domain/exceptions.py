class NotificationNotFoundError(Exception):
    """Raised when marking a notification read that doesn't belong to the user (or doesn't exist)."""
