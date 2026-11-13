
from django.db import transaction

from apps.directions.models import Direction, DirectionTranslation


@transaction.atomic
def create_direction(*, validated_data: dict) -> Direction:
    data = validated_data.copy()
    translations_data = data.pop("translations")

    direction = Direction.objects.create(**data)

    translations = [
        DirectionTranslation(
            direction=direction,
            **translation_data,
        )
        for translation_data in translations_data
    ]

    DirectionTranslation.objects.bulk_create(translations)

    return direction



@transaction.atomic
def update_direction(
    *,
    direction: Direction,
    validated_data: dict,
    replace_translations: bool = False,
) -> Direction:
    data = validated_data.copy()
    translations_data = data.pop("translations", None)

    for field, value in data.items():
        setattr(direction, field, value)

    if data:
        direction.save()

    if translations_data is not None:
        language_codes = [
            item["language_code"]
            for item in translations_data
        ]

        for translation_data in translations_data:
            language_code = translation_data["language_code"]

            defaults = {
                key: value
                for key, value in translation_data.items()
                if key != "language_code"
            }

            DirectionTranslation.objects.update_or_create(
                direction=direction,
                language_code=language_code,
                defaults=defaults,
            )

        if replace_translations:
            direction.translations.exclude(
                language_code__in=language_codes,
            ).delete()

        direction.save(update_fields=["updated_at"])

    return direction



@transaction.atomic
def delete_direction(*, direction: Direction) -> None:
    direction.delete()
