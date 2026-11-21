
from django.db.models import F, QuerySet

from apps.universities.models import (
    University,
    UniversityRevision,
    UniversityMedia,
)


class UniversityMediaSelector:
    """Universitet media fayllarini o'qish uchun querysetlar."""

    @staticmethod
    def get_media_by_revision(revision_id, media_type=None) -> QuerySet:
        """Muayyan revisionga tegishli media fayllarni qaytaradi."""
        qs = (
            UniversityMedia.objects
            .filter(university_revision_id=revision_id)
            .order_by("order", "created_at")
        )
        if media_type:
            qs = qs.filter(media_type=media_type)
        return qs

    @staticmethod
    def get_media_by_id(media_id) -> UniversityMedia | None:
        """ID bo'yicha media faylni qaytaradi."""
        return UniversityMedia.objects.filter(pk=media_id).first()

    @staticmethod
    def get_public_media_by_university(university_id, media_type=None) -> QuerySet:
        """Faqat universitetning joriy published revisionidagi media fayllarni qaytaradi."""
        qs = (
            UniversityMedia.objects
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
            )
            .order_by("order", "created_at")
        )
        if media_type:
            qs = qs.filter(media_type=media_type)
        return qs
