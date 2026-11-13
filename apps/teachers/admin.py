
from django.contrib import admin
from django.utils.html import format_html

from apps.teachers.models import Teacher, TeacherTranslation


class TeacherTranslationInline(admin.TabularInline):
    model = TeacherTranslation
    extra = 0
    max_num = 6
    show_change_link = True


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "photo_preview",
        "order",
        "is_active",
        "created_at",
    )

    list_display_links = ("full_name",)

    list_filter = (
        "is_active",
        "created_at",
    )

    search_fields = (
        "full_name",
        "translations__role",
        "translations__experience",
        "translations__bio",
    )

    ordering = (
        "order",
        "full_name",
    )

    list_editable = (
        "order",
        "is_active",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "photo_preview",
    )

    inlines = (
        TeacherTranslationInline,
    )

    fieldsets = (
        (
            "Teacher Information",
            {
                "fields": (
                    "full_name",
                    "photo",
                    "photo_preview",
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

    @admin.display(description="Photo")
    def photo_preview(self, obj):
        if obj and obj.photo:
            return format_html(
                '<img src="{}" style="max-height: 100px; '
                'max-width: 100px; object-fit: cover; '
                'border-radius: 8px;" />',
                obj.photo.url,
            )

        return "No photo"


@admin.register(TeacherTranslation)
class TeacherTranslationAdmin(admin.ModelAdmin):
    list_display = (
        "teacher",
        "language_code",
        "role",
        "experience",
    )

    list_filter = (
        "language_code",
    )

    search_fields = (
        "teacher__full_name",
        "role",
        "experience",
        "bio",
    )

    ordering = (
        "teacher",
        "language_code",
    )
