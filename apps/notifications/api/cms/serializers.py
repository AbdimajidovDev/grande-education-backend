from rest_framework import serializers

from apps.notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """REST va WebSocket uchun yagona notification payload."""

    class Meta:
        model = Notification
        fields = (
            "id",
            "type",
            "title",
            "message",
            "entity_type",
            "entity_id",
            "data",
            "is_read",
            "read_at",
            "created_at",
        )
        read_only_fields = fields


class NotificationListQuerySerializer(serializers.Serializer):
    is_read = serializers.BooleanField(
        required=False,
        allow_null=True,
        default=None,
        help_text="true — o'qilganlar, false — o'qilmaganlar. Yuborilmasa hammasi.",
    )


class UnreadCountSerializer(serializers.Serializer):
    unread_count = serializers.IntegerField(min_value=0)


class MarkAllReadResponseSerializer(serializers.Serializer):
    updated_count = serializers.IntegerField(min_value=0)
    unread_count = serializers.IntegerField(min_value=0)
