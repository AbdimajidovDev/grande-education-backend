from django.db.models import Exists, F, OuterRef, Prefetch, QuerySet

from apps.universities.models import (
    University,
    UniversityTranslation,
    UniversityTranslationRevision, UniversityRevision,
)


class UniversitySelector:
    """Universitet ma'lumotlarini o'qish uchun selector."""

    @staticmethod
    def get_university_queryset() -> QuerySet:
        """Barcha universitetlarni optimallashtirilgan queryset orqali oladi."""

        return (
            University.objects
            .select_related(
                "published_revision",
                "created_by",
                "updated_by",
            )
            .order_by("-created_at")
        )

    @staticmethod
    def get_university_by_id(university_id) -> University | None:
        """ID orqali universitetni oladi."""

        return (
            UniversitySelector.get_university_queryset()
            .filter(pk=university_id)
            .first()
        )

    @staticmethod
    def get_university_by_id_for_update(
        university_id,
    ) -> University | None:
        """O'zgartirishdan oldin bloklangan universitetni oladi."""

        return (
            University.objects
            .select_for_update()
            .select_related("published_revision")
            .filter(pk=university_id)
            .first()
        )

    @staticmethod
    def get_public_university_queryset() -> QuerySet:
        """
        Faqat PUBLISHED universitetlar va Uzbek tilidagi
        published tarjimasi mavjud universitetlarni oladi.
        """

        published_uzbek_translation = (
            UniversityTranslation.objects
            .filter(
                university_id=OuterRef("pk"),
                language_code="uz",
                published_revision__isnull=False,
                published_revision__status=(
                    UniversityTranslationRevision.Status.PUBLISHED
                ),
                published_revision__translation_id=F("pk"),
            )
        )

        return (
            University.objects
            .filter(
                status=University.Status.PUBLISHED,
                published_revision__isnull=False,
                published_revision__status=(
                    UniversityRevision.Status.PUBLISHED
                ),
                published_revision__university_id=F("pk"),
            )
            .filter(Exists(published_uzbek_translation))
            .select_related("published_revision")
            .order_by("-updated_at")
        )
