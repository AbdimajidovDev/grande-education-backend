import logging
from collections.abc import Iterable

from django.db import DatabaseError, transaction
from django.utils import timezone

from apps.notifications.models import Notification
from apps.notifications.realtime import (
    EVENT_NOTIFICATION_CREATED,
    EVENT_UNREAD_COUNT,
    on_commit_safely,
    send_to_user,
)
from apps.notifications.selectors.notification_selectors import (
    get_unread_count,
    get_unread_counts,
    get_user_notification,
)

logger = logging.getLogger(__name__)


class NotificationNotFoundError(Exception):
    """Notification topilmadi yoki boshqa foydalanuvchiga tegishli."""


def serialize_notification(notification: Notification) -> dict:
    """REST va WebSocket uchun yagona payload (circular importsiz)."""

    from apps.notifications.api.cms.serializers import NotificationSerializer

    return dict(NotificationSerializer(notification).data)


class NotificationService:
    """Bildirishnomalarni yaratish va boshqarishning yagona nuqtasi."""

    @staticmethod
    def _prepare_recipients(recipients: Iterable, actor) -> list:
        """None, nofaol, takroriy va actor'ning o'zini olib tashlaydi."""

        actor_id = getattr(actor, "pk", None)
        unique = {}

        for recipient in recipients or ():
            if recipient is None or getattr(recipient, "pk", None) is None:
                continue
            if not recipient.is_active:
                continue
            if actor_id is not None and recipient.pk == actor_id:
                continue
            unique.setdefault(recipient.pk, recipient)

        return list(unique.values())

    @staticmethod
    def notify_many(
        *,
        recipients: Iterable,
        type: str,
        title: str,
        entity_type: str,
        entity_id,
        message: str = "",
        actor=None,
        data: dict | None = None,
    ) -> list[Notification]:
        """Bir nechta foydalanuvchiga notification yaratadi (bitta INSERT).

        DB yozuvi savepoint ichida bajariladi: notification yozishda xato
        bo'lsa, u logga tushadi va biznes tranzaksiyasi rollback bo'lmaydi.
        WebSocket xabari faqat commitdan keyin yuboriladi.
        """

        prepared = NotificationService._prepare_recipients(recipients, actor)
        if not prepared:
            return []

        actor_id = getattr(actor, "pk", None)
        notifications = [
            Notification(
                recipient=recipient,
                actor_id=actor_id,
                type=type,
                title=title,
                message=message,
                entity_type=entity_type,
                entity_id=str(entity_id),
                data=data or {},
            )
            for recipient in prepared
        ]

        try:
            with transaction.atomic():
                created = Notification.objects.bulk_create(notifications)
        except DatabaseError:
            logger.exception(
                "Notification saqlanmadi (type=%s, entity=%s:%s).",
                type,
                entity_type,
                entity_id,
            )
            return []

        NotificationService._broadcast_created_on_commit(created)
        return created

    @staticmethod
    def notify(
        *,
        recipient,
        type: str,
        title: str,
        entity_type: str,
        entity_id,
        message: str = "",
        actor=None,
        data: dict | None = None,
    ) -> Notification | None:
        created = NotificationService.notify_many(
            recipients=[recipient],
            type=type,
            title=title,
            message=message,
            entity_type=entity_type,
            entity_id=entity_id,
            actor=actor,
            data=data,
        )
        return created[0] if created else None

    @staticmethod
    def _broadcast_created_on_commit(notifications: list[Notification]) -> None:
        payloads = [
            (notification.recipient_id, serialize_notification(notification))
            for notification in notifications
        ]

        def _send():
            # Unread count commitdan keyin bitta so'rov bilan olinadi.
            counts = get_unread_counts(
                user_ids=[recipient_id for recipient_id, _ in payloads]
            )
            for recipient_id, payload in payloads:
                send_to_user(
                    user_id=recipient_id,
                    event={
                        "type": EVENT_NOTIFICATION_CREATED,
                        "notification": payload,
                        "unread_count": counts.get(recipient_id, 0),
                    },
                )

        on_commit_safely(_send, description="notification.created")

    @staticmethod
    def _broadcast_unread_count_on_commit(*, user_id: int) -> None:
        def _send():
            send_to_user(
                user_id=user_id,
                event={
                    "type": EVENT_UNREAD_COUNT,
                    "unread_count": get_unread_count(user_id=user_id),
                },
            )

        on_commit_safely(_send, description="notification.unread_count")

    @staticmethod
    @transaction.atomic
    def mark_as_read(*, user, notification_id) -> Notification:
        """Faqat o'z notificationini o'qilgan qiladi (idempotent)."""

        notification = get_user_notification(
            user_id=user.pk,
            notification_id=notification_id,
        )
        if notification is None:
            raise NotificationNotFoundError("Bildirishnoma topilmadi.")

        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=["is_read", "read_at"])
            # Boshqa ochiq tablar ham badge'ni yangilasin.
            NotificationService._broadcast_unread_count_on_commit(user_id=user.pk)

        return notification

    @staticmethod
    @transaction.atomic
    def mark_all_as_read(*, user) -> int:
        updated = (
            Notification.objects
            .filter(recipient_id=user.pk, is_read=False)
            .update(is_read=True, read_at=timezone.now())
        )
        if updated:
            NotificationService._broadcast_unread_count_on_commit(user_id=user.pk)
        return updated

    @staticmethod
    def get_unread_count(*, user) -> int:
        return get_unread_count(user_id=user.pk)


__all__ = [
    "NotificationNotFoundError",
    "NotificationService",
    "serialize_notification",
]
