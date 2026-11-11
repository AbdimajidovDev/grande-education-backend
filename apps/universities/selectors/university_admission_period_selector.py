from django.db.models import F, QuerySet

from apps.universities.models import (
    University,
    UniversityRevision,
    UniversityAdmissionPeriod,
)


class UniversityAdmissionPeriodSelector:
    """Universitet qabul davrlarini o'qish uchun querysetlar."""

    @staticmethod
    def get_period_queryset() -> QuerySet:
        return (
            UniversityAdmissionPeriod.objects
            .select_related("university_revision")
            .order_by("-application_start_date")
        )

    @staticmethod
    def get_periods_by_revision(
        revision_id,
    ) -> QuerySet:
        """Muayyan revisionga tegishli qabul davrlarini qaytaradi."""

        return (
            UniversityAdmissionPeriod.objects
            .filter(university_revision_id=revision_id)
            .select_related("university_revision")
            .order_by("-application_start_date")
        )

    @staticmethod
    def get_public_periods_by_university(
        university_id,
    ) -> QuerySet:
        """
        Faqat universitetning joriy published revisionidagi
        qabul davrlarini qaytaradi.
        """

        return (
            UniversityAdmissionPeriod.objects
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
            .select_related("university_revision")
            .order_by("-application_start_date")
        )
