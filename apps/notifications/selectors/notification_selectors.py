from collections.abc import Iterable

from django.db.models import Count, QuerySet

from apps.notifications.models import Notification


def get_user_notifications(
    *,
    user_id: int,
    is_read: bool | None = None,
) -> QuerySet[Notification]:
    """Foydalanuvchining o'z bildirishnomalari, eng yangisi birinchi."""

    queryset = Notification.objects.filter(recipient_id=user_id)

    if is_read is not None:
        queryset = queryset.filter(is_read=is_read)

    return queryset.order_by("-created_at", "-id")


def get_user_notification(
    *,
    user_id: int,
    notification_id,
) -> Notification | None:
    """Faqat shu foydalanuvchiga tegishli bildirishnomani qaytaradi."""

    return (
        Notification.objects
        .filter(pk=notification_id, recipient_id=user_id)
        .first()
    )


def get_unread_count(*, user_id: int) -> int:
    return Notification.objects.filter(
        recipient_id=user_id,
        is_read=False,
    ).count()


def get_unread_counts(*, user_ids: Iterable[int]) -> dict[int, int]:
    """Bir nechta foydalanuvchi uchun unread sonini bitta so'rovda qaytaradi."""

    user_ids = list(set(user_ids))
    if not user_ids:
        return {}

    rows = (
        Notification.objects
        .filter(recipient_id__in=user_ids, is_read=False)
        .values("recipient_id")
        .annotate(total=Count("id"))
        .order_by()
    )
    counts = {user_id: 0 for user_id in user_ids}
    counts.update({row["recipient_id"]: row["total"] for row in rows})
    return counts
