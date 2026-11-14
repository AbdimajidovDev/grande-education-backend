from django.db.models import Exists, OuterRef, Prefetch

from apps.education_content.models import (
    HybridTeacher,
    HybridTeacherTranslation,
    LearningComponent,
    LearningComponentTranslation,
)


def get_public_hybrid_teachers(language_code: str):
    available_translations = HybridTeacherTranslation.objects.filter(
        teacher_id=OuterRef("pk"),
        language_code__in=[language_code, "uz"],
    )

    translations = HybridTeacherTranslation.objects.filter(
        language_code__in=[language_code, "uz"],
    ).only(
        "id",
        "teacher_id",
        "language_code",
        "title",
        "subtitle",
        "features",
    )

    return (
        HybridTeacher.objects
        .filter(is_active=True)
        .annotate(
            has_translation=Exists(available_translations),
        )
        .filter(has_translation=True)
        .prefetch_related(
            Prefetch(
                "translations",
                queryset=translations,
                to_attr="prefetched_translations",
            )
        )
        .only(
            "id",
            "badge",
            "chinese_tag",
            "image",
            "order",
        )
        .order_by("order", "id")
    )


def get_public_learning_components(language_code: str):
    available_translations = LearningComponentTranslation.objects.filter(
        component_id=OuterRef("pk"),
        language_code__in=[language_code, "uz"],
    )

    translations = LearningComponentTranslation.objects.filter(
        language_code__in=[language_code, "uz"],
    ).only(
        "id",
        "component_id",
        "language_code",
        "title",
        "description",
    )

    return (
        LearningComponent.objects
        .filter(is_active=True)
        .annotate(
            has_translation=Exists(available_translations),
        )
        .filter(has_translation=True)
        .prefetch_related(
            Prefetch(
                "translations",
                queryset=translations,
                to_attr="prefetched_translations",
            )
        )
        .only(
            "id",
            "icon",
            "chinese_char",
            "order",
        )
        .order_by("order", "id")
    )


def get_admin_hybrid_teachers():
    return (
        HybridTeacher.objects
        .prefetch_related(
            Prefetch(
                "translations",
                queryset=HybridTeacherTranslation.objects.only(
                    "id",
                    "teacher_id",
                    "language_code",
                    "title",
                    "subtitle",
                    "features",
                ),
            )
        )
        .order_by("order", "id")
    )


def get_admin_learning_components():
    return (
        LearningComponent.objects
        .prefetch_related(
            Prefetch(
                "translations",
                queryset=LearningComponentTranslation.objects.only(
                    "id",
                    "component_id",
                    "language_code",
                    "title",
                    "description",
                ),
            )
        )
        .order_by("order", "id")
    )
