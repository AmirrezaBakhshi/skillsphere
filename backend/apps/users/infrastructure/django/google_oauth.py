from dataclasses import dataclass

from django.conf import settings
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from rest_framework.exceptions import AuthenticationFailed


@dataclass
class GoogleProfile:
    sub: str
    email: str
    email_verified: bool


def verify_google_id_token(token: str) -> GoogleProfile:
    """
    Verifies a Google Sign-In ID token client-side flow: the Next.js
    frontend gets this token from Google, sends it here, and we confirm
    it's genuine and meant for our client ID before trusting the claims.
    """
    try:
        claims = google_id_token.verify_oauth2_token(
            token, google_requests.Request(), settings.GOOGLE_OAUTH_CLIENT_ID
        )
    except ValueError as exc:
        raise AuthenticationFailed("Invalid Google token") from exc

    if not claims.get("email_verified"):
        raise AuthenticationFailed("Google account email is not verified")

    return GoogleProfile(
        sub=claims["sub"], email=claims["email"], email_verified=claims["email_verified"]
    )
