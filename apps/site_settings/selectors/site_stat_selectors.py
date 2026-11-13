
from django.db.models import Exists, OuterRef, Prefetch

from apps.site_settings.models import (
    SiteStat,
    SiteStatTranslation,
)


def get_public_site_stats(*, language_code: str):
    languages = (
        [language_code]
        if language_code == "uz"
        else [language_code, "uz"]
    )

    available_translation = SiteStatTranslation.objects.filter(
        stat_id=OuterRef("pk"),
        language_code__in=languages,
    )

    translations_queryset = (
        SiteStatTranslation.objects
        .filter(language_code__in=languages)
        .only(
            "id",
            "stat_id",
            "language_code",
            "label",
            "hint",
        )
    )

    return (
        SiteStat.objects
        .filter(is_active=True)
        .annotate(
            has_translation=Exists(available_translation),
        )
        .filter(has_translation=True)
        .prefetch_related(
            Prefetch(
                "translations",
                queryset=translations_queryset,
                to_attr="available_translations",
            )
        )
        .only(
            "id",
            "number",
            "is_counter",
            "order",
        )
        .order_by("order", "id")
    )


def resolve_site_stat_translation(stat, language_code: str):
    translations = {
        translation.language_code: translation
        for translation in stat.available_translations
    }

    return (
        translations.get(language_code)
        or translations.get("uz")
    )



def get_admin_site_stats():
    return (
        SiteStat.objects
        .prefetch_related(
            Prefetch(
                "translations",
                queryset=SiteStatTranslation.objects.only(
                    "id",
                    "stat_id",
                    "language_code",
                    "label",
                    "hint",
                ),
            )
        )
        .order_by("order", "id")
    )

