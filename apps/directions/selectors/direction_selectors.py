
from django.db.models import Exists, OuterRef, Prefetch

from apps.directions.models import Direction, DirectionTranslation


def get_public_directions(*, language_code: str):
    languages = (
        [language_code]
        if language_code == "uz"
        else [language_code, "uz"]
    )

    available_translation = DirectionTranslation.objects.filter(
        direction_id=OuterRef("pk"),
        language_code__in=languages,
    )

    translations_queryset = (
        DirectionTranslation.objects
        .filter(language_code__in=languages)
        .only(
            "id",
            "direction_id",
            "language_code",
            "number_label",
            "title",
            "summary",
            "tags",
            "goal_text",
            "steps",
            "note",
            "path_text",
        )
    )

    return (
        Direction.objects
        .filter(is_active=True)
        .annotate(
            has_translation=Exists(available_translation),
        )
        .filter(has_translation=True)
        .select_related("inquiry_category")
        .prefetch_related(
            Prefetch(
                "translations",
                queryset=translations_queryset,
                to_attr="available_translations",
            )
        )
        .order_by("order", "id")
    )


def get_admin_directions():
    return (
        Direction.objects
        .select_related("inquiry_category")
        .prefetch_related("translations")
        .order_by("order", "id")
    )


def get_direction_by_id(*, direction_id):
    return (
        Direction.objects
        .select_related("inquiry_category")
        .prefetch_related("translations")
        .filter(pk=direction_id)
        .first()
    )


def resolve_direction_translation(direction, language_code: str):
    translations = {
        translation.language_code: translation
        for translation in direction.available_translations
    }

    return (
        translations.get(language_code)
        or translations.get("uz")
    )
