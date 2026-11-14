from django.db.models import Exists, OuterRef, Prefetch

from apps.education_content.models import (
    UniversityStep,
    UniversityStepPage,
    UniversityStepPageTranslation,
    UniversityStepTranslation,
)


def get_public_university_step_page(language_code: str):
    available_page_translations = UniversityStepPageTranslation.objects.filter(
        page_id=OuterRef("pk"),
        language_code__in=[language_code, "uz"],
    )

    page_translations = UniversityStepPageTranslation.objects.filter(
        language_code__in=[language_code, "uz"],
    ).only(
        "id",
        "page_id",
        "language_code",
        "title",
        "subtitle",
    )

    available_step_translations = UniversityStepTranslation.objects.filter(
        step_id=OuterRef("pk"),
        language_code__in=[language_code, "uz"],
    )

    step_translations = UniversityStepTranslation.objects.filter(
        language_code__in=[language_code, "uz"],
    ).only(
        "id",
        "step_id",
        "language_code",
        "action_verb",
        "title",
        "description",
    )

    steps = (
        UniversityStep.objects
        .filter(is_active=True)
        .annotate(
            has_translation=Exists(available_step_translations),
        )
        .filter(has_translation=True)
        .prefetch_related(
            Prefetch(
                "translations",
                queryset=step_translations,
                to_attr="prefetched_translations",
            )
        )
        .only(
            "id",
            "page_id",
            "step_number",
            "dazhi_numeral",
            "chinese_char",
            "pinyin",
            "chinese_concept",
            "image",
            "order",
        )
        .order_by("order", "step_number")
    )

    return (
        UniversityStepPage.objects
        .filter(is_active=True)
        .annotate(
            has_translation=Exists(available_page_translations),
        )
        .filter(has_translation=True)
        .prefetch_related(
            Prefetch(
                "translations",
                queryset=page_translations,
                to_attr="prefetched_translations",
            ),
            Prefetch(
                "steps",
                queryset=steps,
                to_attr="prefetched_steps",
            ),
        )
        .only(
            "id",
            "is_active",
        )
        .first()
    )


def get_admin_university_step_pages():
    return (
        UniversityStepPage.objects
        .prefetch_related(
            Prefetch(
                "translations",
                queryset=UniversityStepPageTranslation.objects.only(
                    "id",
                    "page_id",
                    "language_code",
                    "title",
                    "subtitle",
                ),
            ),
            Prefetch(
                "steps",
                queryset=(
                    UniversityStep.objects
                    .prefetch_related(
                        Prefetch(
                            "translations",
                            queryset=UniversityStepTranslation.objects.only(
                                "id",
                                "step_id",
                                "language_code",
                                "action_verb",
                                "title",
                                "description",
                            ),
                        )
                    )
                    .only(
                        "id",
                        "page_id",
                        "step_number",
                        "dazhi_numeral",
                        "chinese_char",
                        "pinyin",
                        "chinese_concept",
                        "image",
                        "order",
                        "is_active",
                    )
                    .order_by("order", "step_number")
                ),
                to_attr="prefetched_steps",
            ),
        )
        .order_by("-created_at")
    )


def get_admin_university_steps():
    return (
        UniversityStep.objects
        .select_related("page")
        .prefetch_related(
            Prefetch(
                "translations",
                queryset=UniversityStepTranslation.objects.only(
                    "id",
                    "step_id",
                    "language_code",
                    "action_verb",
                    "title",
                    "description",
                ),
            )
        )
        .order_by("page_id", "order", "step_number")
    )
