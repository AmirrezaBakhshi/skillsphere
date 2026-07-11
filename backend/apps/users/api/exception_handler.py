from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

from apps.users.domain.exceptions import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from apps.notifications.domain.exceptions import NotificationNotFoundError
from apps.projects.domain.exceptions import InvalidFileError, ProjectNotFoundError

_DOMAIN_ERROR_STATUS = {
    UserAlreadyExistsError: status.HTTP_409_CONFLICT,
    InvalidCredentialsError: status.HTTP_401_UNAUTHORIZED,
    UserNotFoundError: status.HTTP_404_NOT_FOUND,
    NotificationNotFoundError: status.HTTP_404_NOT_FOUND,
    ProjectNotFoundError: status.HTTP_404_NOT_FOUND,
    InvalidFileError: status.HTTP_422_UNPROCESSABLE_ENTITY,
}


def domain_exception_handler(exc, context):
    """
    Lets domain exceptions raised from application services surface as
    sensible HTTP responses without views needing their own try/except
    blocks for every use case.
    """
    for exc_type, http_status in _DOMAIN_ERROR_STATUS.items():
        if isinstance(exc, exc_type):
            return Response({"detail": str(exc)}, status=http_status)

    return exception_handler(exc, context)
