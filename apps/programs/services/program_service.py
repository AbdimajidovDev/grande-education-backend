
from django.db.models import Exists, OuterRef, Prefetch

from apps.programs.models import Program, ProgramTranslation


def get_public_programs(language_code: str):
    """
    Returns published programs that have either the requested
    translation or the Uzbek fallback translation.
    """

    supported_languages = ProgramTranslation.Language.values

    if language_code not in supported_languages:
        raise ValueError(f"Unsupported language: {language_code}")

    languages = (
        [language_code]
        if language_code == "uz"
        else [language_code, "uz"]
    )

    available_translation = ProgramTranslation.objects.filter(
        program_id=OuterRef("pk"),
        language_code__in=languages,
    )

    translations_queryset = (
        ProgramTranslation.objects
        .filter(language_code__in=languages)
        .only(
            "id",
            "program_id",
            "language_code",
            "title",
            "subtitle",
            "description",
            "features",
        )
    )

    return (
        Program.objects
        .filter(is_published=True)
        .annotate(
            has_translation=Exists(available_translation)
        )
        .filter(has_translation=True)
        .prefetch_related(
            Prefetch(
                "translations",
                queryset=translations_queryset,
                to_attr="available_translations",
            )
        )
        .order_by("order", "-created_at")
    )


def resolve_program_translation(program, language_code: str):
    """
    Resolves requested translation or Uzbek fallback.
    Uses prefetched translations to avoid additional queries.
    """

    translations = {
        translation.language_code: translation
        for translation in program.available_translations
    }

    return (
        translations.get(language_code)
        or translations.get("uz")
    )
