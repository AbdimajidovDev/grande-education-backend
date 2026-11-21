
from django.db.models import F, QuerySet

from apps.universities.models import (
    University,
    UniversityRevision,
    UniversityMajor,
)


class UniversityMajorSelector:
    """Universitet yo'nalishlarini (majors) o'qish uchun querysetlar."""

    @staticmethod
    def get_majors_by_revision(revision_id) -> QuerySet:
        """Muayyan revisionga tegishli barcha yo'nalishlarni qaytaradi."""
        return (
            UniversityMajor.objects
            .filter(university_revision_id=revision_id)
            .prefetch_related("translations")
            .order_by("order", "created_at")
        )

    @staticmethod
    def get_major_by_id(major_id) -> UniversityMajor | None:
        """ID bo'yicha yo'nalishni qaytaradi."""
        return (
            UniversityMajor.objects
            .filter(pk=major_id)
            .prefetch_related("translations")
            .first()
        )

    @staticmethod
    def get_public_majors_by_university(university_id) -> QuerySet:
        """Faqat universitetning joriy published revisionidagi faol yo'nalishlarni qaytaradi."""
        return (
            UniversityMajor.objects
            .filter(
                university_revision__university_id=university_id,
                university_revision__university__status=(
                    University.Status.PUBLISHED
                ),
                university_revision__status=(
                    UniversityRevision.Status.PUBLISHED
                ),
                university_revision_id=F(
                    "university_revision__university__published_revision_id"
                ),
                is_active=True,
            )
            .prefetch_related("translations")
            .order_by("order", "created_at")
        )
