"""
ASGI config for chats project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/howto/deployment/asgi/
"""

import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "chats.settings")  # NOQA
django_asgi_app = get_asgi_application()  # NOQA

from chats.apps.accounts.authentication.channels.middleware import (  # NOQA
    TokenAuthMiddleware,
)
from chats.apps.api.websockets.rooms.routing import websocket_urlpatterns  # NOQA

application = ProtocolTypeRouter(
    {
        # "http": django_asgi_app,
        "websocket": TokenAuthMiddleware(URLRouter(websocket_urlpatterns)),
    }
)
