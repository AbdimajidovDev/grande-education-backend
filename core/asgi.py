"""
ASGI config for core project.

HTTP so'rovlar Django'ning standart ASGI ilovasiga, WebSocket esa
Channels'ga yo'naltiriladi. Production'da HTTP gunicorn (WSGI) orqali
xizmat qiladi; bu ilova daphne orqali asosan `/ws/` uchun ishlatiladi.

https://docs.djangoproject.com/en/6.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Django app registry Channels/consumer importlaridan oldin tayyor bo'lishi shart.
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.security.websocket import OriginValidator  # noqa: E402
from django.conf import settings  # noqa: E402

from apps.notifications.auth import JWTCookieAuthMiddleware  # noqa: E402
from apps.notifications.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": OriginValidator(
        JWTCookieAuthMiddleware(URLRouter(websocket_urlpatterns)),
        settings.WEBSOCKET_ALLOWED_ORIGINS,
    ),
})
