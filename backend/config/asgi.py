import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

# Stage 1 only needs plain HTTP. The ProtocolTypeRouter with a websocket
# routing table for notifications/chat gets added once Channels consumers
# exist (see notifications app, later stage).
application = get_asgi_application()
