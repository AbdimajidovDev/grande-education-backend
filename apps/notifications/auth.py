"""WebSocket uchun cookie'dagi JWT autentifikatsiya adapteri.

HTTP tomonda ishlatiladigan `CookieJWTAuthentication` DRF Request obyektini
va CSRF tekshiruvini talab qiladi, shuning uchun u ASGI scope'da bevosita
ishlamaydi. Bu adapter xuddi shu cookie (`settings.AUTH_COOKIE_ACCESS`) va
simplejwt'ning o'sha validatsiyasidan (imzo, muddat, token turi, faol
foydalanuvchi) foydalanadi. CSRF o'rniga WebSocket'da Origin tekshiruvi
(`channels.security.websocket.OriginValidator`) qo'llanadi.

Token yoki cookie qiymati hech qachon logga yozilmaydi.
"""

import logging

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.http.cookie import parse_cookie
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

logger = logging.getLogger(__name__)


def _get_cookie(scope, name: str) -> str | None:
    for header_name, header_value in scope.get("headers", ()):
        if header_name == b"cookie":
            return parse_cookie(header_value.decode("latin1")).get(name)
    return None


@database_sync_to_async
def _authenticate(raw_token: str):
    """(user, exp_timestamp) yoki (AnonymousUser, None) qaytaradi."""

    authenticator = JWTAuthentication()

    try:
        validated_token = authenticator.get_validated_token(raw_token)
        user = authenticator.get_user(validated_token)
    except (InvalidToken, TokenError, AuthenticationFailed) as exc:
        logger.info("WebSocket JWT rad etildi: %s", exc.__class__.__name__)
        return AnonymousUser(), None

    if not user.is_active:
        return AnonymousUser(), None

    return user, validated_token.get("exp")


class JWTCookieAuthMiddleware(BaseMiddleware):
    """Handshake vaqtida `scope["user"]` va `scope["token_exp"]` ni o'rnatadi."""

    async def __call__(self, scope, receive, send):
        scope = dict(scope)
        scope["user"] = AnonymousUser()
        scope["token_exp"] = None

        raw_token = _get_cookie(scope, settings.AUTH_COOKIE_ACCESS)
        if raw_token:
            scope["user"], scope["token_exp"] = await _authenticate(raw_token)

        return await super().__call__(scope, receive, send)
