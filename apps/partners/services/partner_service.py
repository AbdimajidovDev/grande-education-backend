
from django.db import transaction

from apps.partners.models import Partner


@transaction.atomic
def create_partner(*, validated_data: dict) -> Partner:
    """
    Creates a new partner.
    """
    return Partner.objects.create(**validated_data)


@transaction.atomic
def update_partner(
    *,
    partner: Partner,
    validated_data: dict,
) -> Partner:
    """
    Updates an existing partner.
    """
    for field, value in validated_data.items():
        setattr(partner, field, value)

    partner.save()

    return partner


@transaction.atomic
def delete_partner(*, partner: Partner) -> None:
    """
    Deletes an existing partner.
    """
    partner.delete()
