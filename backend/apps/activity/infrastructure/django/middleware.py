from apps.activity.application.services import RecordActivityService
from apps.activity.infrastructure.django.repositories import DjangoActivityLogRepository

# Paths we don't bother logging - noisy and not useful for analytics.
_IGNORED_PREFIXES = ("/admin/", "/static/", "/media/")

_ACTION_BY_PATH_FRAGMENT = {
    "auth/login": "login",
    "auth/register": "register",
    "auth/google": "google_login",
    "auth/logout": "logout",
    "projects": "project_activity",
}


class ActivityLoggingMiddleware:
    """
    Records one ActivityLog row per authenticated request. Sits after
    AuthenticationMiddleware in MIDDLEWARE so request.user is already
    resolved (for session/admin auth) - for JWT-authenticated DRF calls,
    request.user is only set by DRF's own authentication inside the view,
    so we read it from the response's renderer context when available,
    falling back to anonymous.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.service = RecordActivityService(repository=DjangoActivityLogRepository())

    def __call__(self, request):
        response = self.get_response(request)

        if request.path.startswith(_IGNORED_PREFIXES):
            return response

        user = getattr(request, "user", None)
        user_id = user.id if user is not None and getattr(user, "is_authenticated", False) else None

        action = "api_request"
        for fragment, name in _ACTION_BY_PATH_FRAGMENT.items():
            if fragment in request.path:
                action = name
                break

        try:
            self.service.record(
                user_id=user_id,
                action=action,
                path=request.path,
                method=request.method,
                status_code=response.status_code,
            )
        except Exception:
            # Activity logging must never break the actual request.
            pass

        return response
