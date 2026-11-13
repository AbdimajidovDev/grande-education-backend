
from django.contrib import admin

from apps.site_settings.models import (
    Office,
    SiteStat,
    SiteStatTranslation,
    ContactInfo,
    ContactAddress,
    WorkingHour,
    SocialLink,
)


# =====================================================
# Site Statistics
# =====================================================

class SiteStatTranslationInline(admin.TabularInline):
    model = SiteStatTranslation
    extra = 0
    max_num = 6
    show_change_link = True


@admin.register(SiteStat)
class SiteStatAdmin(admin.ModelAdmin):
    list_display = (
        "number",
        "is_counter",
        "order",
        "is_active",
        "created_at",
    )
    list_display_links = ("number",)
    list_filter = (
        "is_active",
        "is_counter",
        "created_at",
    )
    search_fields = (
        "number",
        "translations__label",
        "translations__hint",
    )
    ordering = ("order", "id")
    list_editable = (
        "order",
        "is_active",
    )
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )
    inlines = (
        SiteStatTranslationInline,
    )
    fieldsets = (
        (
            "Statistic information",
            {
                "fields": (
                    "id",
                    "number",
                    "is_counter",
                    "order",
                    "is_active",
                )
            },
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )


@admin.register(SiteStatTranslation)
class SiteStatTranslationAdmin(admin.ModelAdmin):
    list_display = (
        "stat",
        "language_code",
        "label",
        "hint",
    )
    list_filter = ("language_code",)
    search_fields = (
        "stat__number",
        "label",
        "hint",
    )
    ordering = (
        "stat__order",
        "language_code",
    )
    readonly_fields = ("id",)


# =====================================================
# Office
# =====================================================

class ContactInfoInline(admin.StackedInline):
    model = ContactInfo
    extra = 0
    max_num = 1
    can_delete = True


class ContactAddressInline(admin.StackedInline):
    model = ContactAddress
    extra = 0
    max_num = 1
    can_delete = True


class WorkingHourInline(admin.TabularInline):
    model = WorkingHour
    extra = 0
    max_num = 7
    ordering = ("weekday",)


class SocialLinkInline(admin.TabularInline):
    model = SocialLink
    extra = 0
    ordering = ("order", "platform")


@admin.register(Office)
class OfficeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "is_main",
        "is_active",
        "created_at",
    )
    list_display_links = ("name",)
    list_filter = (
        "is_main",
        "is_active",
        "created_at",
    )
    search_fields = (
        "name",
        "contact_info__phone_raw",
        "contact_info__email",
        "address__city",
    )
    ordering = (
        "-is_main",
        "name",
    )
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )
    inlines = (
        ContactInfoInline,
        ContactAddressInline,
        WorkingHourInline,
        SocialLinkInline,
    )
    fieldsets = (
        (
            "Office information",
            {
                "fields": (
                    "id",
                    "name",
                    "is_main",
                    "is_active",
                )
            },
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )


# =====================================================
# Contact Information
# =====================================================

@admin.register(ContactInfo)
class ContactInfoAdmin(admin.ModelAdmin):
    list_display = (
        "office",
        "phone_raw",
        "email",
        "updated_at",
    )
    search_fields = (
        "office__name",
        "phone_raw",
        "email",
    )
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )


@admin.register(ContactAddress)
class ContactAddressAdmin(admin.ModelAdmin):
    list_display = (
        "office",
        "city",
        "street",
    )
    search_fields = (
        "office__name",
        "city",
        "street",
        "landmark",
    )
    readonly_fields = (
        "id",
    )



# =====================================================
# Working Hours
# =====================================================

@admin.register(WorkingHour)
class WorkingHourAdmin(admin.ModelAdmin):
    list_display = (
        "office",
        "weekday",
        "opens_at",
        "closes_at",
        "is_closed",
    )
    list_filter = (
        "office",
        "weekday",
        "is_closed",
    )
    ordering = (
        "office",
        "weekday",
    )
    readonly_fields = ("id",)


# =====================================================
# Social Links
# =====================================================

@admin.register(SocialLink)
class SocialLinkAdmin(admin.ModelAdmin):
    list_display = (
        "office",
        "platform",
        "username",
        "url",
        "is_active",
        "order",
    )
    list_filter = (
        "office",
        "platform",
        "is_active",
    )
    search_fields = (
        "office__name",
        "username",
        "url",
    )
    ordering = (
        "office",
        "order",
        "platform",
    )
    list_editable = (
        "is_active",
        "order",
    )
    readonly_fields = ("id",)
