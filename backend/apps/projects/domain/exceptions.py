class InvalidFileError(Exception):
    """Raised when an uploaded file fails type/size validation."""


class ProjectNotFoundError(Exception):
    """Raised when a project lookup (by id, for a given owner) finds nothing."""
