import asyncio
import time

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from apps.notifications.realtime import user_group_name
from apps.notifications.selectors.notification_selectors import get_unread_count

# Frontend shu kodlarga qarab harakat qiladi (docs/notifications.md).
CLOSE_UNAUTHENTICATED = 4401   # token yo'q/yaroqsiz/muddati tugagan → refresh + reconnect
CLOSE_SESSION_TERMINATED = 4403  # xodim nofaol qilindi → qayta ulanmaslik


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    """Har bir xodim faqat o'zining `user_{id}` group'iga ulanadi.

    Group nomi faqat autentifikatsiya qilingan foydalanuvchidan olinadi —
    client URL, query yoki xabar orqali boshqa group tanlay olmaydi.
    """

    group_name: str | None = None
    _expiry_task: asyncio.Task | None = None

    async def connect(self):
        user = self.scope.get("user")

        if user is None or not user.is_authenticated or not user.is_active:
            # Accept + close: brauzer close code'ni (4401) ko'ra oladi.
            await self.accept()
            await self.close(code=CLOSE_UNAUTHENTICATED)
            return

        self.group_name = user_group_name(user.pk)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        self._schedule_token_expiry(self.scope.get("token_exp"))

        await self.send_json({
            "type": "unread_count",
            "unread_count": await self._get_unread_count(user.pk),
        })

    async def disconnect(self, code):
        if self._expiry_task is not None:
            self._expiry_task.cancel()
            self._expiry_task = None

        if self.group_name is not None:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            self.group_name = None

    async def receive_json(self, content, **kwargs):
        if isinstance(content, dict) and content.get("type") == "ping":
            await self.send_json({"type": "pong"})
            return

        await self.send_json({
            "type": "error",
            "code": "unsupported_event",
            "message": "Faqat {\"type\": \"ping\"} xabari qabul qilinadi.",
        })

    # ------------------------------------------------------------------
    # Channel layer event handlerlari (realtime.py dagi type'lar)
    # ------------------------------------------------------------------

    async def notification_created(self, event):
        await self.send_json({
            "type": "notification.created",
            "data": event["notification"],
            "unread_count": event["unread_count"],
        })

    async def notification_unread_count(self, event):
        await self.send_json({
            "type": "unread_count",
            "unread_count": event["unread_count"],
        })

    async def permissions_changed(self, event):
        await self.send_json({"type": "permissions_changed"})

    async def session_terminate(self, event):
        await self.send_json({"type": "session_terminated"})
        await self.close(code=CLOSE_SESSION_TERMINATED)

    # ------------------------------------------------------------------

    def _schedule_token_expiry(self, token_exp) -> None:
        """Access token muddati tugashi bilan ulanishni 4401 bilan yopadi."""

        if not token_exp:
            return

        delay = max(float(token_exp) - time.time(), 0)
        self._expiry_task = asyncio.create_task(self._close_on_expiry(delay))

    async def _close_on_expiry(self, delay: float) -> None:
        await asyncio.sleep(delay)
        await self.send_json({"type": "token_expired"})
        await self.close(code=CLOSE_UNAUTHENTICATED)

    @staticmethod
    @database_sync_to_async
    def _get_unread_count(user_id: int) -> int:
        return get_unread_count(user_id=user_id)
