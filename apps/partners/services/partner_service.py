
import logging

from django.db import transaction

from apps.partners.models import Partner


logger = logging.getLogger(__name__)


def _schedule_file_deletion(*, storage, file_name: str) -> None:
    if not file_name:
        return

    def delete_file():
        try:
            storage.delete(file_name)
        except Exception:
            logger.exception(
                "Failed to delete partner logo: %s",
                file_name,
            )

    transaction.on_commit(delete_file)


@transaction.atomic
def create_partner(*, validated_data: dict) -> Partner:
    return Partner.objects.create(**validated_data)


@transaction.atomic
def update_partner(
    *,
    partner: Partner,
    validated_data: dict,
) -> Partner:
    data = validated_data.copy()

    old_logo_name = (
        partner.logo.name
        if partner.logo
        else None
    )
    logo_storage = partner.logo.storage

    for field, value in data.items():
        setattr(partner, field, value)

    if data:
        partner.save()

    new_logo_name = (
        partner.logo.name
        if partner.logo
        else None
    )

    if old_logo_name and old_logo_name != new_logo_name:
        _schedule_file_deletion(
            storage=logo_storage,
            file_name=old_logo_name,
        )

    return partner


@transaction.atomic
def delete_partner(*, partner: Partner) -> None:
    logo_name = partner.logo.name if partner.logo else None
    logo_storage = partner.logo.storage

    partner.delete()

    if logo_name:
        _schedule_file_deletion(
            storage=logo_storage,
            file_name=logo_name,
        )
