
from django.contrib import admin

from apps.partners.models import Partner


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "website",
        "order",
        "is_active",
        "created_at",
    )

    list_display_links = ("name",)

    list_filter = (
        "is_active",
        "created_at",
    )

    search_fields = (
        "name",
        "description",
        "website",
    )

    ordering = (
        "order",
        "name",
    )

    list_editable = (
        "order",
        "is_active",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "logo_preview",
    )

    fieldsets = (
        (
            "Partner Information",
            {
                "fields": (
                    "name",
                    "description",
                    "website",
                    "logo",
                    "logo_preview",
                ),
            },
        ),
        (
            "Display Settings",
            {
                "fields": (
                    "order",
                    "is_active",
                ),
            },
        ),
        (
            "System Information",
            {
                "fields": (
                    "id",
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def logo_preview(self, obj):
        if obj and obj.logo:
            return admin.display_for_field(
                obj.logo.url,
                obj,
                "logo",
            )

        return "No logo"

    logo_preview.short_description = "Logo Preview"
