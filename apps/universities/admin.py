
from django.contrib import admin
from django.utils.html import format_html

from .models import (
    University,
    UniversityRevision,
    UniversityTranslation,
    UniversityTranslationRevision,
    UniversityAdmissionPeriod,
    UniversityMajor,
    UniversityMajorTranslation,
    UniversityMedia,
)


class UniversityMajorInline(admin.TabularInline):
    model = UniversityMajor
    extra = 0
    fields = ("order", "is_active", "created_at")
    readonly_fields = ("created_at",)
    show_change_link = True


class UniversityMediaInline(admin.TabularInline):
    model = UniversityMedia
    extra = 0
    fields = ("thumbnail_preview", "media_type", "order", "caption", "created_at")
    readonly_fields = ("thumbnail_preview", "created_at")
    show_change_link = True

    def thumbnail_preview(self, obj):
        if obj.file:
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 80px; object-fit: cover; border-radius: 4px;" />',
                obj.file.url,
            )
        return "-"
    thumbnail_preview.short_description = "Preview"


class UniversityRevisionInline(admin.TabularInline):
    model = UniversityRevision
    extra = 0
    fields = (
        "revision_number",
        "city",
        "country",
        "status",
        "created_by",
        "created_at",
    )
    readonly_fields = fields
    show_change_link = True


class UniversityTranslationInline(admin.TabularInline):
    model = UniversityTranslation
    extra = 0
    fields = (
        "language_code",
        "slug",
        "published_revision",
    )
    readonly_fields = fields
    show_change_link = True


@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "status",
        "published_revision",
        "created_by",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("id",)
    readonly_fields = (
        "id",
        "created_by",
        "updated_by",
        "published_revision",
        "created_at",
        "updated_at",
    )
    inlines = (
        UniversityRevisionInline,
        UniversityTranslationInline,
    )
    list_select_related = (
        "created_by",
        "updated_by",
        "published_revision",
    )
    ordering = ("-created_at",)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user

        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(UniversityRevision)
class UniversityRevisionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "university",
        "revision_number",
        "city",
        "chinese_name",
        "established_year",
        "students_count",
        "status",
        "created_by",
        "published_at",
    )
    list_filter = ("status", "country", "created_at")
    search_fields = ("city", "chinese_name", "country", "university__id")
    inlines = (UniversityMajorInline, UniversityMediaInline)
    readonly_fields = (
        "id",
        "revision_number",
        "created_by",
        "approved_by",
        "approved_at",
        "published_at",
        "created_at",
        "updated_at",
    )
    list_select_related = (
        "university",
        "created_by",
        "approved_by",
    )
    ordering = ("-created_at",)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user

        super().save_model(request, obj, form, change)


@admin.register(UniversityTranslation)
class UniversityTranslationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "university",
        "language_code",
        "slug",
        "published_revision",
        "created_at",
    )
    list_filter = ("language_code",)
    search_fields = (
        "university__id",
        "slug",
    )
    readonly_fields = (
        "id",
        "slug",
        "published_revision",
        "created_at",
        "updated_at",
    )
    list_select_related = (
        "university",
        "published_revision",
    )


@admin.register(UniversityTranslationRevision)
class UniversityTranslationRevisionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "translation",
        "revision_number",
        "name",
        "status",
        "created_by",
        "approved_by",
        "published_at",
    )
    list_filter = (
        "status",
        "translation__language_code",
        "created_at",
    )
    search_fields = (
        "name",
        "slug",
        "translation__university__id",
    )
    readonly_fields = (
        "id",
        "revision_number",
        "created_by",
        "approved_by",
        "approved_at",
        "published_at",
        "created_at",
        "updated_at",
    )
    list_select_related = (
        "translation",
        "translation__university",
        "created_by",
        "approved_by",
    )
    ordering = ("-created_at",)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user

        super().save_model(request, obj, form, change)


@admin.register(UniversityAdmissionPeriod)
class UniversityAdmissionPeriodAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "university_revision",
        "name",
        "application_start_date",
        "application_end_date",
        "study_start_date",
        "study_end_date",
    )
    list_filter = (
        "application_start_date",
        "study_start_date",
    )
    search_fields = (
        "name",
        "university_revision__city",
        "university_revision__country",
    )
    list_select_related = ("university_revision",)
    ordering = ("application_start_date",)


class UniversityMajorTranslationInline(admin.TabularInline):
    model = UniversityMajorTranslation
    extra = 0
    fields = ("language_code", "title", "description")


@admin.register(UniversityMajor)
class UniversityMajorAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "university_revision",
        "order",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active", "created_at")
    search_fields = ("id", "university_revision__id", "translations__title")
    inlines = (UniversityMajorTranslationInline,)
    ordering = ("order", "created_at")


@admin.register(UniversityMedia)
class UniversityMediaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "thumbnail_preview",
        "university_revision",
        "media_type",
        "order",
        "caption",
        "created_at",
    )
    list_filter = ("media_type", "created_at")
    search_fields = ("caption", "university_revision__id")
    readonly_fields = ("thumbnail_preview", "created_at", "updated_at")
    ordering = ("order", "created_at")

    def thumbnail_preview(self, obj):
        if obj.file:
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 80px; object-fit: cover; border-radius: 4px;" />',
                obj.file.url,
            )
        return "-"
    thumbnail_preview.short_description = "Preview"

