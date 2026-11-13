
from django.contrib import admin

from apps.directions.models import Direction, DirectionTranslation


class DirectionTranslationInline(admin.TabularInline):
    model = DirectionTranslation
    extra = 0
    max_num = 6


@admin.register(Direction)
class DirectionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "inquiry_category",
        "order",
        "is_active",
        "created_at",
    )

    list_filter = (
        "is_active",
        "inquiry_category",
    )

    search_fields = (
        "id",
        "translations__title",
    )

    ordering = ("order",)

    inlines = [DirectionTranslationInline]


@admin.register(DirectionTranslation)
class DirectionTranslationAdmin(admin.ModelAdmin):
    list_display = (
        "direction",
        "language_code",
        "title",
    )

    list_filter = ("language_code",)

    search_fields = (
        "title",
        "direction__id",
    )
