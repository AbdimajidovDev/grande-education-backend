from django.db.models import F, QuerySet

from apps.universities.models import (
    UniversityTranslation,
    UniversityTranslationRevision, University, UniversityRevision,
)
from apps.universities.constants import SUPPORTED_LANGUAGES


class UniversityTranslationSelector:
    """Universitet tarjimalarini o'qish uchun selector."""

    @staticmethod
    def get_translation_queryset() -> QuerySet:
        """Barcha tarjimalarni optimallashtirilgan queryset orqali oladi."""

        return (
            UniversityTranslation.objects
            .select_related(
                "university",
                "published_revision",
            )
            .order_by("university_id", "language_code")
        )


    @staticmethod
    def get_translations_by_university(
        university_id,
    ) -> QuerySet:
        """Universitetning barcha tarjimalarini oladi."""

        return (
            UniversityTranslationSelector.get_translation_queryset()
            .filter(university_id=university_id)
        )

    @staticmethod
    def get_translation_by_id(
        translation_id,
    ) -> UniversityTranslation | None:
        """ID orqali tarjimani oladi."""

        return (
            UniversityTranslationSelector.get_translation_queryset()
            .filter(pk=translation_id)
            .first()
        )

    @staticmethod
    def get_translation_by_language(
        *,
        university_id,
        language_code: str,
    ) -> UniversityTranslation | None:
        """Universitet tarjimasini til kodi orqali oladi."""

        return (
            UniversityTranslationSelector.get_translation_queryset()
            .filter(
                university_id=university_id,
                language_code=language_code,
            )
            .first()
        )

    @staticmethod
    def get_published_translation(
            *,
            university_id,
            language_code: str,
    ) -> UniversityTranslation | None:
        """Universitetning muayyan tildagi published tarjimasini oladi."""

        return (
            UniversityTranslationSelector.get_translation_queryset()
            .filter(
                university_id=university_id,
                university__status=University.Status.PUBLISHED,
                university__published_revision__status=UniversityRevision.Status.PUBLISHED,
                language_code=language_code,
                published_revision__isnull=False,
                published_revision__status=(
                    UniversityTranslationRevision.Status.PUBLISHED
                ),
                published_revision__translation_id=F("pk"),
            )
            .first()
        )

    @staticmethod
    def get_revision_queryset() -> QuerySet:
        """Tarjima revisionlarini optimallashtirilgan queryset orqali oladi."""

        return (
            UniversityTranslationRevision.objects
            .select_related(
                "translation",
                "translation__university",
                "created_by",
                "approved_by",
            )
            .order_by("-created_at")
        )

    @staticmethod
    def get_revisions_by_translation(
        translation_id,
    ) -> QuerySet:
        """Muayyan tarjimaning barcha revisionlarini oladi."""

        return (
            UniversityTranslationSelector.get_revision_queryset()
            .filter(translation_id=translation_id)
            .order_by("-revision_number")
        )

    @staticmethod
    def get_revision_by_id(
        revision_id,
    ) -> UniversityTranslationRevision | None:
        """ID orqali tarjima revisionini oladi."""

        return (
            UniversityTranslationSelector.get_revision_queryset()
            .filter(pk=revision_id)
            .first()
        )

    @staticmethod
    def get_public_translation(
        *,
        university_id,
        language_code: str,
    ) -> UniversityTranslation | None:
        """
        So'ralgan tildagi published tarjimani qaytaradi.
        Mavjud bo'lmasa, Uzbek tarjimasiga fallback qiladi.
        """

        language_code = (language_code or "").strip().lower()

        if language_code not in SUPPORTED_LANGUAGES:
            language_code = "uz"

        translation = (
            UniversityTranslationSelector.get_published_translation(
                university_id=university_id,
                language_code=language_code,
            )
        )

        if translation is not None:
            return translation

        if language_code == "uz":
            return None

        return (
            UniversityTranslationSelector.get_published_translation(
                university_id=university_id,
                language_code="uz",
            )
        )