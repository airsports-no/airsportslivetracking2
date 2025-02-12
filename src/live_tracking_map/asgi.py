"""
ASGI config for live_tracking_map project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'live_tracking_map.settings')
asgi_app = get_asgi_application()
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
import display.routing

application = ProtocolTypeRouter({
    "http": asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            display.routing.websocket_urlpatterns
        )
    )
})
