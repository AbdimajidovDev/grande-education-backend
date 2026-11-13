
from django.contrib import admin
from django.utils.html import format_html

from apps.programs.models import Program, ProgramTranslation


class ProgramTranslationInline(admin.TabularInline):
    model = ProgramTranslation
    extra = 0
    max_num = 6
    show_change_link = True


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = (
        "slug",
        "category",
        "format",
        "pricing_type",
        "price_amount",
        "currency",
        "order",
        "is_published",
        "created_at",
    )

    list_display_links = ("slug",)

    list_filter = (
        "category",
        "format",
        "pricing_type",
        "price_period",
        "is_published",
    )

    search_fields = (
        "slug",
        "translations__title",
        "translations__subtitle",
        "translations__description",
    )

    ordering = (
        "order",
        "slug",
    )

    list_editable = (
        "order",
        "is_published",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "image_preview",
    )

    inlines = (
        ProgramTranslationInline,
    )

    fieldsets = (
        (
            "Program Information",
            {
                "fields": (
                    "slug",
                    "category",
                    "format",
                    "duration",
                ),
            },
        ),
        (
            "Pricing",
            {
                "fields": (
                    "pricing_type",
                    "price_amount",
                    "currency",
                    "price_period",
                ),
            },
        ),
        (
            "Media",
            {
                "fields": (
                    "image",
                    "image_preview",
                ),
            },
        ),
        (
            "Display Settings",
            {
                "fields": (
                    "order",
                    "is_published",
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

    def image_preview(self, obj):
        if obj and obj.image:
            return format_html(
                '<img src="{}" style="max-height: 120px; '
                'max-width: 200px; object-fit: contain;" />',
                obj.image.url,
            )

        return "No image"

    image_preview.short_description = "Image Preview"


@admin.register(ProgramTranslation)
class ProgramTranslationAdmin(admin.ModelAdmin):
    list_display = (
        "program",
        "language_code",
        "title",
    )

    list_filter = (
        "language_code",
    )

    search_fields = (
        "program__slug",
        "title",
        "subtitle",
    )

    ordering = (
        "program",
        "language_code",
    )
