from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken


@database_sync_to_async
def _get_user_from_access_token(raw_token: str):
    from apps.users.infrastructure.django.models import User

    try:
        validated = AccessToken(raw_token)
        return User.objects.get(id=validated["user_id"])
    except (TokenError, InvalidToken, User.DoesNotExist):
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """
    WebSocket connections can't send a normal `Authorization` header from
    a browser's native WebSocket API, so the same short-lived access
    token used for REST calls gets passed as a query string param
    instead: `ws://.../ws/chat/<id>/?token=<access_token>`. This is the
    WebSocket-world equivalent of Stage 1's CookieJWTAuthentication - same
    token, same validation rules (simplejwt's AccessToken class), just a
    different place to find it, since cookies/headers work differently
    for a persistent WebSocket connection than for one-shot HTTP requests.
    """

    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()
        token = parse_qs(query_string).get("token", [None])[0]

        scope["user"] = (
            await _get_user_from_access_token(token) if token else AnonymousUser()
        )
        return await super().__call__(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    return JWTAuthMiddleware(inner)
