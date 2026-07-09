from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    """
    Access tokens travel in the standard `Authorization: Bearer <token>`
    header (short-lived, held in frontend memory/state - never in a
    cookie, so an XSS can't read it via document.cookie). Only the
    long-lived refresh token lives in an httponly cookie; that cookie is
    read directly by the refresh view (api/views.py), not through this
    authentication class. This subclass exists purely so the DDD/adapter
    boundary is explicit and so cookie-based refresh handling can be
    layered in here later without touching REST_FRAMEWORK settings again.
    """

    pass
