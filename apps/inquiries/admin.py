
from django.contrib import admin

from apps.inquiries.models import (
    Inquiry,
    InquiryActivity,
    InquiryCategory,
    InquiryCategoryTranslation,
)


class InquiryCategoryTranslationInline(admin.TabularInline):
    model = InquiryCategoryTranslation
    extra = 0
    fields = (
        "language_code",
        "name",
        "description",
    )


@admin.register(InquiryCategory)
class InquiryCategoryAdmin(admin.ModelAdmin):
    list_display = (
        "slug",
        "id",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active",)
    search_fields = ("slug",)
    readonly_fields = ("created_at", "updated_at")
    inlines = (InquiryCategoryTranslationInline,)


@admin.register(InquiryCategoryTranslation)
class InquiryCategoryTranslationAdmin(admin.ModelAdmin):
    list_display = (
        "category",
        "language_code",
        "name",
        "updated_at",
    )
    list_filter = ("language_code",)
    search_fields = (
        "name",
        "category__slug",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )


class InquiryActivityInline(admin.TabularInline):
    model = InquiryActivity
    extra = 0
    can_delete = False
    readonly_fields = (
        "actor",
        "action",
        "note",
        "created_at",
    )

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "phone_number",
        "category",
        "university",
        "status",
        "assignee",
        "created_at",
    )
    list_filter = (
        "status",
        "category",
        "contact_method",
        "created_at",
    )
    search_fields = (
        "full_name",
        "phone_number",
        "email",
    )
    readonly_fields = (
        "id",
        "idempotency_key",
        "created_at",
        "updated_at",
    )
    inlines = (InquiryActivityInline,)


@admin.register(InquiryActivity)
class InquiryActivityAdmin(admin.ModelAdmin):
    list_display = (
        "inquiry",
        "actor",
        "action",
        "created_at",
    )
    list_filter = ("action", "created_at")
    search_fields = (
        "inquiry__full_name",
        "note",
    )
    readonly_fields = (
        "inquiry",
        "actor",
        "action",
        "note",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
