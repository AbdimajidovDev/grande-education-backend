
from django.db import transaction

from apps.site_settings.models import (
    SiteStat,
    SiteStatTranslation,
)


@transaction.atomic
def create_site_stat(*, validated_data: dict) -> SiteStat:
    data = validated_data.copy()
    translations_data = data.pop("translations")

    stat = SiteStat.objects.create(**data)

    SiteStatTranslation.objects.bulk_create(
        [
            SiteStatTranslation(
                stat=stat,
                **translation_data,
            )
            for translation_data in translations_data
        ]
    )

    return stat


@transaction.atomic
def update_site_stat(
    *,
    stat: SiteStat,
    validated_data: dict,
    replace_translations: bool = False,
) -> SiteStat:
    data = validated_data.copy()
    translations_data = data.pop("translations", None)

    for field, value in data.items():
        setattr(stat, field, value)

    if data:
        stat.save()

    if translations_data is not None:
        language_codes = []

        for translation_data in translations_data:
            translation_data = translation_data.copy()
            language_code = translation_data.pop("language_code")
            language_codes.append(language_code)

            SiteStatTranslation.objects.update_or_create(
                stat=stat,
                language_code=language_code,
                defaults=translation_data,
            )

        if replace_translations:
            stat.translations.exclude(
                language_code__in=language_codes
            ).delete()

        stat.save(update_fields=["updated_at"])

    return stat


@transaction.atomic
def delete_site_stat(*, stat: SiteStat) -> None:
    stat.delete()
