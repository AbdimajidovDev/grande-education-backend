from django.contrib import admin

from apps.notifications.models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "recipient",
        "type",
        "title",
        "entity_type",
        "is_read",
        "created_at",
    )
    list_filter = ("type", "entity_type", "is_read", "created_at")
    search_fields = ("title", "message", "recipient__username", "entity_id")
    list_select_related = ("recipient",)
    raw_id_fields = ("recipient", "actor")
    readonly_fields = (
        "id",
        "recipient",
        "actor",
        "type",
        "title",
        "message",
        "entity_type",
        "entity_id",
        "data",
        "read_at",
        "created_at",
    )

    def has_add_permission(self, request):
        return False
