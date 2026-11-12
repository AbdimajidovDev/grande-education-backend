
from django.db.models import (
    CharField,
    OuterRef,
    Subquery,
)
from django.db.models.functions import Coalesce

from apps.inquiries.models import (
    InquiryCategory,
    InquiryCategoryTranslation,
)


def get_active_inquiry_categories(language_code="uz"):
    requested_translation = (
        InquiryCategoryTranslation.objects
        .filter(
            category_id=OuterRef("pk"),
            language_code=language_code,
        )
        .order_by()
    )

    fallback_translation = (
        InquiryCategoryTranslation.objects
        .filter(
            category_id=OuterRef("pk"),
            language_code="uz",
        )
        .order_by()
    )

    return (
        InquiryCategory.objects
        .filter(is_active=True)
        .annotate(
            translated_name=Subquery(
                requested_translation.values("name")[:1],
                output_field=CharField(),
            ),
            fallback_name=Subquery(
                fallback_translation.values("name")[:1],
                output_field=CharField(),
            ),
            translated_description=Subquery(
                requested_translation.values("description")[:1],
                output_field=CharField(),
            ),
            fallback_description=Subquery(
                fallback_translation.values("description")[:1],
                output_field=CharField(),
            ),
        )
        .annotate(
            name=Coalesce(
                "translated_name",
                "fallback_name",
                output_field=CharField(),
            ),
            description=Coalesce(
                "translated_description",
                "fallback_description",
                output_field=CharField(),
            ),
        )
        .filter(name__isnull=False)
        .values(
            "id",
            "slug",
            "name",
            "description",
        )
    )
