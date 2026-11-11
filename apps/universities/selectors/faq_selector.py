
from django.db.models import F, QuerySet

from apps.universities.models import (
    FAQ,
    FAQTranslation,
    FAQTranslationRevision,
)


class FAQSelector:
    """FAQ ma'lumotlarini olish uchun optimallashtirilgan selectorlar."""

    @staticmethod
    def get_faq_queryset() -> QuerySet:
        return FAQ.objects.order_by("order", "-created_at")

    @staticmethod
    def get_faq_by_id(faq_id):
        return FAQ.objects.filter(pk=faq_id).first()

    @staticmethod
    def get_translations_by_faq(faq_id) -> QuerySet:
        return (
            FAQTranslation.objects
            .filter(faq_id=faq_id)
            .select_related("published_revision")
            .order_by("language_code")
        )

    @staticmethod
    def get_revisions_by_translation(translation_id) -> QuerySet:
        return (
            FAQTranslationRevision.objects
            .filter(translation_id=translation_id)
            .select_related("created_by", "approved_by")
            .order_by("-revision_number")
        )

    @staticmethod
    def get_public_faqs(language_code: str) -> QuerySet:
        return (
            FAQTranslation.objects
            .filter(
                faq__is_active=True,
                language_code=language_code,
                published_revision__isnull=False,
                published_revision__status=(
                    FAQTranslationRevision.Status.PUBLISHED
                ),
                published_revision__translation_id=F("pk"),
            )
            .select_related(
                "faq",
                "published_revision",
            )
            .order_by("faq__order", "-faq__created_at")
        )

    @staticmethod
    def get_translation_by_id(translation_id):
        return (
            FAQTranslation.objects
            .filter(pk=translation_id)
            .select_related("faq", "published_revision")
            .first()
        )

    @staticmethod
    def get_revision_by_id(revision_id):
        return (
            FAQTranslationRevision.objects
            .filter(pk=revision_id)
            .select_related(
                "translation",
                "created_by",
                "approved_by",
            )
            .first()
        )

