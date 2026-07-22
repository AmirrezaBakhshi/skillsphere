import os

import django
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

django_asgi_app = get_asgi_application()

# Imported after django.setup() / get_asgi_application(): these modules
# import Django models, which aren't ready to import until app registry
# setup has finished.
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402

from apps.chat.infrastructure.channels.jwt_auth_middleware import (  # noqa: E402
    JWTAuthMiddlewareStack,
)
from apps.chat.infrastructure.channels.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": JWTAuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
    }
)

