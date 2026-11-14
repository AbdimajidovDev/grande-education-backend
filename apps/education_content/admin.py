from django.contrib import admin

from .models import (
    HybridTeacher,
    HybridTeacherTranslation,
    LearningComponent,
    LearningComponentTranslation,
    UniversityStepPage,
    UniversityStepPageTranslation,
    UniversityStep,
    UniversityStepTranslation,
)


# =========================================================
# Hybrid Teachers
# =========================================================

class HybridTeacherTranslationInline(admin.TabularInline):
    model = HybridTeacherTranslation
    extra = 1
    fields = (
        "language_code",
        "title",
        "subtitle",
        "features",
    )


@admin.register(HybridTeacher)
class HybridTeacherAdmin(admin.ModelAdmin):
    list_display = (
        "badge",
        "chinese_tag",
        "order",
        "is_active",
        "created_at",
    )
    list_editable = ("order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("badge", "chinese_tag")
    ordering = ("order",)
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = (HybridTeacherTranslationInline,)


# =========================================================
# Learning Components
# =========================================================

class LearningComponentTranslationInline(admin.TabularInline):
    model = LearningComponentTranslation
    extra = 1
    fields = (
        "language_code",
        "title",
        "description",
    )


@admin.register(LearningComponent)
class LearningComponentAdmin(admin.ModelAdmin):
    list_display = (
        "chinese_char",
        "icon",
        "order",
        "is_active",
    )
    list_editable = ("icon", "order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("chinese_char", "icon")
    ordering = ("order",)
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = (LearningComponentTranslationInline,)


# =========================================================
# University Steps Page
# =========================================================

class UniversityStepPageTranslationInline(admin.TabularInline):
    model = UniversityStepPageTranslation
    extra = 1
    fields = (
        "language_code",
        "title",
        "subtitle",
    )


class UniversityStepInline(admin.TabularInline):
    model = UniversityStep
    extra = 0
    fields = (
        "step_number",
        "dazhi_numeral",
        "chinese_char",
        "pinyin",
        "chinese_concept",
        "image",
        "order",
        "is_active",
    )
    ordering = ("order", "step_number")


@admin.register(UniversityStepPage)
class UniversityStepPageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active",)
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = (
        UniversityStepPageTranslationInline,
        UniversityStepInline,
    )


# =========================================================
# University Step Translations
# =========================================================

class UniversityStepTranslationInline(admin.TabularInline):
    model = UniversityStepTranslation
    extra = 1
    fields = (
        "language_code",
        "action_verb",
        "title",
        "description",
    )


@admin.register(UniversityStep)
class UniversityStepAdmin(admin.ModelAdmin):
    list_display = (
        "step_number",
        "chinese_char",
        "pinyin",
        "page",
        "order",
        "is_active",
    )
    list_filter = ("is_active", "page")
    search_fields = (
        "chinese_char",
        "pinyin",
        "chinese_concept",
    )
    ordering = ("page", "order", "step_number")
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = (UniversityStepTranslationInline,)
