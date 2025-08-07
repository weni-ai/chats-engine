import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "chats.settings")
django_asgi_app = get_asgi_application()

from chats.apps.accounts.authentication.channels.middleware import TokenAuthMiddleware
from chats.apps.api.websockets.rooms.routing import websocket_urlpatterns


def http_404_response(scope):
    async def asgi(receive, send):
        await send(
            {
                "type": "http.response.start",
                "status": 404,
                "headers": [[b"content-type", b"text/plain"]],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": b"WebSocket-only pod",
            }
        )

    return asgi


application = ProtocolTypeRouter(
    {
        "http": http_404_response,
        "websocket": TokenAuthMiddleware(URLRouter(websocket_urlpatterns)),
    }
)
