
from django.db import transaction

from apps.site_settings.models import (
    Office,
    ContactInfo,
    ContactAddress,
    WorkingHour,
    SocialLink,
)


@transaction.atomic
def create_office(*, validated_data: dict) -> Office:
    data = validated_data.copy()

    contact_info_data = data.pop("contact_info")
    address_data = data.pop("address")
    working_hours_data = data.pop("working_hours", [])
    social_links_data = data.pop("social_links", [])

    office = Office.objects.create(**data)

    ContactInfo.objects.create(
        office=office,
        **contact_info_data,
    )

    ContactAddress.objects.create(
        office=office,
        **address_data,
    )

    if working_hours_data:
        WorkingHour.objects.bulk_create(
            [
                WorkingHour(
                    office=office,
                    **item,
                )
                for item in working_hours_data
            ]
        )

    if social_links_data:
        SocialLink.objects.bulk_create(
            [
                SocialLink(
                    office=office,
                    **item,
                )
                for item in social_links_data
            ]
        )

    return office


@transaction.atomic
def update_office(
    *,
    office: Office,
    validated_data: dict,
) -> Office:
    data = validated_data.copy()

    contact_info_data = data.pop("contact_info", None)
    address_data = data.pop("address", None)
    working_hours_data = data.pop("working_hours", None)
    social_links_data = data.pop("social_links", None)

    for field, value in data.items():
        setattr(office, field, value)

    if data:
        office.save()

    if contact_info_data is not None:
        ContactInfo.objects.update_or_create(
            office=office,
            defaults=contact_info_data,
        )

    if address_data is not None:
        ContactAddress.objects.update_or_create(
            office=office,
            defaults=address_data,
        )

    if working_hours_data is not None:
        office.working_hours.all().delete()

        WorkingHour.objects.bulk_create(
            [
                WorkingHour(
                    office=office,
                    **item,
                )
                for item in working_hours_data
            ]
        )

    if social_links_data is not None:
        office.social_links.all().delete()

        SocialLink.objects.bulk_create(
            [
                SocialLink(
                    office=office,
                    **item,
                )
                for item in social_links_data
            ]
        )

    return office


@transaction.atomic
def delete_office(*, office: Office) -> None:
    office.delete()
