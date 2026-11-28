"""Channel layer orqali foydalanuvchi group'lariga event yuborish.

Bu modul ataylab boshqa app'larning service/selectorlarini import qilmaydi —
rbac va users service'lari undan circular import xavfisiz foydalanadi.

Barcha funksiyalar `transaction.on_commit()` orqali chaqiriladi: biznes
tranzaksiyasi rollback bo'lsa, frontendga "soxta" event bormaydi.
Channel layer (Redis) ishlamay qolsa xato logga yoziladi, lekin
DB'dagi ma'lumot va biznes amali saqlanib qoladi.
"""

import asyncio
import logging
from collections.abc import Callable, Iterable

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.db import transaction

logger = logging.getLogger(__name__)


# Consumer handler nomlari (`type` dagi nuqta pastki chiziqqa aylanadi).
EVENT_NOTIFICATION_CREATED = "notification.created"
EVENT_UNREAD_COUNT = "notification.unread_count"
EVENT_PERMISSIONS_CHANGED = "permissions.changed"
EVENT_SESSION_TERMINATE = "session.terminate"


def user_group_name(user_id: int) -> str:
    return f"user_{user_id}"


# Redis javob bermay qolsa API so'rovi uzoq kutib qolmasligi uchun.
DEFAULT_SEND_TIMEOUT_SECONDS = 2.0


def _send_timeout() -> float:
    return float(
        getattr(settings, "NOTIFICATIONS_WS_SEND_TIMEOUT", DEFAULT_SEND_TIMEOUT_SECONDS)
    )


async def _group_send_with_timeout(channel_layer, group: str, event: dict) -> None:
    await asyncio.wait_for(
        channel_layer.group_send(group, event),
        timeout=_send_timeout(),
    )


def on_commit_safely(func: Callable[[], None], *, description: str) -> None:
    """Callback'ni commitdan keyin ishga tushiradi; xatosi API'ga ko'tarilmaydi.

    Commit allaqachon bo'lgan — callback ichidagi har qanday xato (Redis,
    channel layer konfiguratsiyasi, unread count so'rovi) javobni 500 ga
    aylantirmasligi kerak. Xato to'liq traceback bilan logga yoziladi.
    `robust=True` qo'shimcha himoya: Django ham xatoni ushlab logga yozadi.
    """

    def _run():
        try:
            func()
        except Exception:
            logger.exception("Real-time callback bajarilmadi (%s).", description)

    transaction.on_commit(_run, robust=True)


def send_to_user(*, user_id: int, event: dict) -> bool:
    """Eventni darhol yuboradi. Muvaffaqiyatli bo'lsa True qaytaradi."""

    try:
        channel_layer = get_channel_layer()
        if channel_layer is None:
            logger.warning("CHANNEL_LAYERS sozlanmagan; real-time event yuborilmadi.")
            return False

        async_to_sync(_group_send_with_timeout)(
            channel_layer,
            user_group_name(user_id),
            event,
        )
    except Exception:
        # Real-time yetkazish ixtiyoriy kanal: xato yashirilmaydi, logga
        # to'liq traceback bilan yoziladi, DB'dagi notification saqlanadi.
        logger.exception(
            "Real-time event yuborilmadi (user_id=%s, event=%s).",
            user_id,
            event.get("type"),
        )
        return False

    return True


def send_to_users_on_commit(*, user_ids: Iterable[int], event: dict) -> None:
    user_ids = sorted(set(user_ids))
    if not user_ids:
        return

    def _send():
        for user_id in user_ids:
            send_to_user(user_id=user_id, event=event)

    on_commit_safely(_send, description=f"{event.get('type')} -> {len(user_ids)} user")


def notify_permissions_changed(*, user_ids: Iterable[int]) -> None:
    """Rol/permission o'zgarganda frontend menyu va huquqlarni qayta yuklaydi."""

    send_to_users_on_commit(
        user_ids=user_ids,
        event={"type": EVENT_PERMISSIONS_CHANGED},
    )


def terminate_user_sessions(*, user_id: int) -> None:
    """Nofaol qilingan xodimning barcha ochiq WebSocket ulanishlarini yopadi."""

    send_to_users_on_commit(
        user_ids=[user_id],
        event={"type": EVENT_SESSION_TERMINATE},
    )
