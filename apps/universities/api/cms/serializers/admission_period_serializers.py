
from rest_framework import serializers

from apps.universities.models import UniversityAdmissionPeriod


class UniversityAdmissionPeriodCreateSerializer(serializers.ModelSerializer):
    """Yangi qabul davri yaratish uchun."""

    class Meta:
        model = UniversityAdmissionPeriod
        fields = [
            "name",
            "application_start_date",
            "application_end_date",
            "study_start_date",
            "study_end_date",
        ]

    def validate(self, attrs):
        application_start = attrs.get("application_start_date")
        application_end = attrs.get("application_end_date")

        study_start = attrs.get("study_start_date")
        study_end = attrs.get("study_end_date")

        if (
            application_start
            and application_end
            and application_start > application_end
        ):
            raise serializers.ValidationError({
                "application_end_date": (
                    "Ariza tugash sanasi boshlanish sanasidan "
                    "oldin bo'lishi mumkin emas."
                )
            })

        if (
            study_start
            and study_end
            and study_start > study_end
        ):
            raise serializers.ValidationError({
                "study_end_date": (
                    "O'qish tugash sanasi boshlanish sanasidan "
                    "oldin bo'lishi mumkin emas."
                )
            })

        return attrs


class UniversityAdmissionPeriodUpdateSerializer(
    serializers.ModelSerializer
):
    """Mavjud qabul davrini qisman tahrirlash uchun."""

    class Meta:
        model = UniversityAdmissionPeriod
        fields = [
            "name",
            "application_start_date",
            "application_end_date",
            "study_start_date",
            "study_end_date",
        ]
        extra_kwargs = {
            field: {"required": False}
            for field in fields
        }

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError(
                "Qabul davri nomi bo'sh bo'lishi mumkin emas."
            )
        return value.strip()

    def validate(self, attrs):
        instance = self.instance

        application_start = attrs.get(
            "application_start_date",
            instance.application_start_date,
        )
        application_end = attrs.get(
            "application_end_date",
            instance.application_end_date,
        )

        study_start = attrs.get(
            "study_start_date",
            instance.study_start_date,
        )
        study_end = attrs.get(
            "study_end_date",
            instance.study_end_date,
        )

        if application_start > application_end:
            raise serializers.ValidationError({
                "application_end_date": (
                    "Ariza tugash sanasi boshlanish sanasidan "
                    "oldin bo'lishi mumkin emas."
                )
            })

        if (
            study_start is not None
            and study_end is not None
            and study_start > study_end
        ):
            raise serializers.ValidationError({
                "study_end_date": (
                    "O'qish tugash sanasi boshlanish sanasidan "
                    "oldin bo'lishi mumkin emas."
                )
            })

        return attrs


class UniversityAdmissionPeriodListSerializer(serializers.ModelSerializer):
    """CMS'da qabul davrlari ro'yxati uchun."""

    class Meta:
        model = UniversityAdmissionPeriod
        fields = [
            "id",
            "name",
            "application_start_date",
            "application_end_date",
            "study_start_date",
            "study_end_date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
