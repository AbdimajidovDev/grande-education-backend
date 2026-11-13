
from django.db.models import Prefetch

from apps.site_settings.models import (
    Office,
    WorkingHour,
    SocialLink,
)


def get_public_contact_office():
    working_hours_queryset = (
        WorkingHour.objects
        .only(
            "id",
            "office_id",
            "weekday",
            "opens_at",
            "closes_at",
            "is_closed",
        )
        .order_by("weekday")
    )

    social_links_queryset = (
        SocialLink.objects
        .filter(is_active=True)
        .only(
            "id",
            "office_id",
            "platform",
            "username",
            "url",
            "order",
        )
        .order_by("order", "platform")
    )

    return (
        Office.objects
        .filter(is_active=True)
        .select_related(
            "contact_info",
            "address",
        )
        .prefetch_related(
            Prefetch(
                "working_hours",
                queryset=working_hours_queryset,
                to_attr="available_working_hours",
            ),
            Prefetch(
                "social_links",
                queryset=social_links_queryset,
                to_attr="available_social_links",
            ),
        )
        .only(
            "id",
            "name",
            "is_main",
            "contact_info__id",
            "contact_info__office_id",
            "contact_info__phone_raw",
            "contact_info__email",
            "address__id",
            "address__office_id",
            "address__city",
            "address__street",
            "address__landmark",
            "address__map_url",
        )
        .order_by("-is_main", "name")
        .first()
    )



def get_admin_offices():
    working_hours_queryset = (
        WorkingHour.objects
        .only(
            "id",
            "office_id",
            "weekday",
            "opens_at",
            "closes_at",
            "is_closed",
        )
        .order_by("weekday")
    )

    social_links_queryset = (
        SocialLink.objects
        .only(
            "id",
            "office_id",
            "platform",
            "username",
            "url",
            "is_active",
            "order",
        )
        .order_by("order", "platform")
    )

    return (
        Office.objects
        .select_related(
            "contact_info",
            "address",
        )
        .prefetch_related(
            Prefetch(
                "working_hours",
                queryset=working_hours_queryset,
            ),
            Prefetch(
                "social_links",
                queryset=social_links_queryset,
            ),
        )
        .order_by("-is_main", "name")
    )

