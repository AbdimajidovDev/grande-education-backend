
from rest_framework import serializers

from apps.universities.models import UniversityAdmissionPeriod


class PublicUniversityAdmissionPeriodSerializer(
    serializers.ModelSerializer
):
    """Saytga chiqariladigan qabul davrlari."""

    class Meta:
        model = UniversityAdmissionPeriod
        fields = [
            "id",
            "name",
            "application_start_date",
            "application_end_date",
            "study_start_date",
            "study_end_date",
        ]
        read_only_fields = fields
