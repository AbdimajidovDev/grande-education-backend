from django.db.models import QuerySet

from apps.universities.models import UniversityRevision


class UniversityRevisionSelector:
    """Universitet revisionlarini o'qish uchun selector."""

    @staticmethod
    def get_revision_queryset() -> QuerySet:
        """Barcha revisionlarni optimallashtirilgan queryset orqali oladi."""

        return (
            UniversityRevision.objects
            .select_related(
                "university",
                "created_by",
                "approved_by",
            )
            .order_by("-created_at")
        )

    @staticmethod
    def get_revisions_by_university(
        university_id,
    ) -> QuerySet:
        """Universitetning barcha revisionlari tarixini oladi."""

        return (
            UniversityRevisionSelector.get_revision_queryset()
            .filter(university_id=university_id)
            .order_by("-revision_number")
        )

    @staticmethod
    def get_revision_by_id(
        revision_id,
    ) -> UniversityRevision | None:
        """ID orqali revisionni oladi."""

        return (
            UniversityRevisionSelector.get_revision_queryset()
            .filter(pk=revision_id)
            .first()
        )

    @staticmethod
    def get_revisions_by_status(
        status: str,
    ) -> QuerySet:
        """Berilgan statusdagi revisionlarni oladi."""

        return (
            UniversityRevisionSelector.get_revision_queryset()
            .filter(status=status)
        )