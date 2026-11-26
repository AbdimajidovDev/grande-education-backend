
from django.contrib import admin
from django.utils.html import format_html

from .models import (
    MediaCleanupTask,
    University,
    UniversityAuditLog,
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
    fields = ("title_preview", "order", "is_active", "created_at")
    readonly_fields = ("title_preview", "created_at")
    show_change_link = True

    def title_preview(self, obj):
        if obj and obj.pk:
            trans = obj.translations.filter(language_code="uz").first() or obj.translations.first()
            return trans.title if trans else f"Major #{obj.id}"
        return "-"
    title_preview.short_description = "Yo'nalish nomi"


class UniversityMediaInline(admin.TabularInline):
    model = UniversityMedia
    extra = 1
    fields = ("thumbnail_preview", "file", "media_type", "order", "caption", "created_at")
    readonly_fields = ("thumbnail_preview", "created_at")
    show_change_link = True

    def thumbnail_preview(self, obj):
        if obj and obj.file:
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
        "chinese_name",
        "city",
        "city_native",
        "established_year",
        "students_count",
        "international_students_count",
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
        "published_name",
        "published_revision",
    )
    readonly_fields = fields
    show_change_link = True

    def published_name(self, obj):
        if obj and obj.published_revision:
            return obj.published_revision.name
        return "-"
    published_name.short_description = "Nashr qilingan nom"


@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "get_name",
        "get_chinese_name",
        "get_city_country",
        "get_logo_preview",
        "status",
        "created_by",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = (
        "id",
        "revisions__chinese_name",
        "revisions__city",
        "translations__revisions__name",
    )
    readonly_fields = (
        "id",
        "get_published_overview",
        "get_published_majors",
        "get_published_media",
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

    def get_name(self, obj):
        trans = obj.translations.filter(language_code="uz").first() or obj.translations.first()
        if trans and trans.published_revision:
            return trans.published_revision.name
        elif trans:
            rev = trans.revisions.first()
            return rev.name if rev else "-"
        return "-"
    get_name.short_description = "Nomi"

    def get_chinese_name(self, obj):
        if obj.published_revision:
            return obj.published_revision.chinese_name or "-"
        first_rev = obj.revisions.first()
        return first_rev.chinese_name if first_rev else "-"
    get_chinese_name.short_description = "Xitoycha nomi"

    def get_city_country(self, obj):
        rev = obj.published_revision or obj.revisions.first()
        if rev:
            return f"{rev.city}, {rev.country}"
        return "-"
    get_city_country.short_description = "Shahar / Davlat"

    def get_logo_preview(self, obj):
        rev = obj.published_revision or obj.revisions.first()
        if rev:
            logo = rev.media_items.filter(media_type="logo").first()
            if logo and logo.file:
                return format_html(
                    '<img src="{}" style="height: 35px; width: 35px; object-fit: contain; border-radius: 4px;" />',
                    logo.file.url,
                )
        return "-"
    get_logo_preview.short_description = "Logo"

    def get_published_overview(self, obj):
        rev = obj.published_revision
        if not rev:
            return format_html("<em>Hozircha nashr qilingan versiya mavjud emas.</em>")

        trans = obj.translations.filter(language_code="uz").first() or obj.translations.first()
        trans_rev = trans.published_revision if trans else None

        badges_html = ""
        if trans_rev and trans_rev.features:
            badges = [
                f"<span style='background:#e0f2fe;color:#0369a1;padding:2px 8px;border-radius:12px;font-size:12px;margin-right:4px;'>{f}</span>"
                for f in trans_rev.features
            ]
            badges_html = f"<div style='margin-top: 10px;'><strong>Xususiyatlar / Teglar:</strong> {' '.join(badges)}</div>"

        accom_html = (
            f"<div style='margin-top: 8px;'><strong>Yotoqxona:</strong> {trans_rev.accommodation_info}</div>"
            if trans_rev and trans_rev.accommodation_info else ""
        )
        note_html = (
            f"<div style='margin-top: 6px;'><strong>Qabul talablari:</strong> {trans_rev.admission_note}</div>"
            if trans_rev and trans_rev.admission_note else ""
        )

        html = f"""
        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin-bottom: 12px;">
            <h4 style="margin: 0 0 8px 0; color: #1e293b; font-size: 16px;">
                {trans_rev.name if trans_rev else "Nomsiz"} ({rev.chinese_name or "Xitoycha nomi yo'q"})
            </h4>
            <p style="margin: 0 0 8px 0; color: #64748b; font-style: italic;">
                {trans_rev.subtitle if trans_rev and trans_rev.subtitle else "Qisqa shior kiritilmagan"}
            </p>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; margin-top: 10px;">
                <div><strong>Joylashuv:</strong> {rev.city} ({rev.city_native or "-"}), {rev.country}</div>
                <div><strong>Tashkil topgan yili:</strong> {rev.established_year or "-"}</div>
                <div><strong>Jami talabalar:</strong> {rev.students_count or "-"}</div>
                <div><strong>Xalqaro talabalar:</strong> {rev.international_students_count or "-"}</div>
            </div>
            {badges_html}
            {accom_html}
            {note_html}
        </div>
        """
        return format_html(html)
    get_published_overview.short_description = "Nashr qilingan umumiy ko'rinish"

    def get_published_majors(self, obj):
        rev = obj.published_revision
        if not rev:
            return "-"
        majors = rev.majors.all().prefetch_related("translations")
        if not majors.exists():
            return "Yo'nalishlar mavjud emas"

        items = []
        for m in majors:
            t = m.translations.filter(language_code="uz").first() or m.translations.first()
            title = t.title if t else "Nomsiz"
            status_badge = "<span style='color:green;'>● Faol</span>" if m.is_active else "<span style='color:red;'>● Nofaol</span>"
            items.append(f"<li><strong>#{m.order}</strong> {title} — {status_badge}</li>")
        return format_html("<ul style='margin: 0; padding-left: 20px;'>" + "".join(items) + "</ul>")
    get_published_majors.short_description = "Nashr qilingan yo'nalishlar"

    def get_published_media(self, obj):
        rev = obj.published_revision
        if not rev:
            return "-"
        media_items = rev.media_items.all().order_by("order")
        if not media_items.exists():
            return "Media fayllar mavjud emas"

        cards = []
        for m in media_items:
            if m.file:
                caption_div = f"<div style='font-size: 10px; color: #94a3b8; max-width: 100px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;'>{m.caption}</div>" if m.caption else ""
                cards.append(f"""
                <div style="display: inline-block; margin-right: 12px; text-align: center; vertical-align: top;">
                    <a href="{m.file.url}" target="_blank">
                        <img src="{m.file.url}" style="height: 70px; width: 100px; object-fit: cover; border-radius: 6px; border: 1px solid #cbd5e1;" />
                    </a>
                    <div style="font-size: 11px; color: #475569; margin-top: 2px;">
                        <span style="text-transform: uppercase; font-weight: bold;">{m.media_type}</span> ({m.order})
                    </div>
                    {caption_div}
                </div>
                """)
        return format_html('<div style="display: flex; flex-wrap: wrap; gap: 8px;">' + "".join(cards) + '</div>')
    get_published_media.short_description = "Nashr qilingan rasmlar (Logo, Cover, Galereya)"

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
    fieldsets = (
        (
            "Asosiy metrikalar",
            {
                "fields": (
                    "university",
                    "revision_number",
                    "chinese_name",
                    "city",
                    "city_native",
                    "country",
                    "established_year",
                    "students_count",
                    "international_students_count",
                )
            },
        ),
        (
            "Holat va Tasdiqlash",
            {
                "fields": (
                    "status",
                    "rejection_reason",
                    "created_by",
                    "approved_by",
                    "approved_at",
                    "published_at",
                    "scheduled_publish_at",
                    "created_at",
                    "updated_at",
                )
            },
        ),
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
        "subtitle",
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
        "subtitle",
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
    fieldsets = (
        (
            "Asosiy matnlar",
            {
                "fields": (
                    "translation",
                    "revision_number",
                    "name",
                    "slug",
                    "subtitle",
                    "description",
                )
            },
        ),
        (
            "Qo'shimcha ma'lumotlar",
            {
                "fields": (
                    "features",
                    "accommodation_info",
                    "admission_note",
                )
            },
        ),
        (
            "SEO",
            {
                "fields": (
                    "seo_title",
                    "seo_description",
                )
            },
        ),
        (
            "Holat va Tarix",
            {
                "fields": (
                    "status",
                    "rejection_reason",
                    "created_by",
                    "approved_by",
                    "approved_at",
                    "published_at",
                    "scheduled_publish_at",
                    "created_at",
                    "updated_at",
                )
            },
        ),
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


@admin.register(UniversityAuditLog)
class UniversityAuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "action",
        "object_type",
        "object_id",
        "object_repr",
        "actor_identifier",
        "timestamp",
    )
    list_filter = ("action", "object_type", "timestamp")
    search_fields = ("object_id", "object_repr", "actor_identifier")
    readonly_fields = (
        "id",
        "actor",
        "actor_identifier",
        "action",
        "object_type",
        "object_id",
        "object_repr",
        "timestamp",
        "metadata",
    )
    ordering = ("-timestamp",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(MediaCleanupTask)
class MediaCleanupTaskAdmin(admin.ModelAdmin):
    list_display = ("id", "file_path", "status", "attempts", "created_at", "completed_at")
    list_filter = ("status", "created_at")
    search_fields = ("file_path", "last_error")
    readonly_fields = (
        "id",
        "file_path",
        "status",
        "attempts",
        "last_error",
        "created_at",
        "updated_at",
        "completed_at",
    )
    ordering = ("-created_at",)

