from rest_framework import serializers

from apps.universities.models import UniversityRevision


class UniversityRevisionCreateSerializer(serializers.Serializer):
    """Universitet uchun yangi revision yaratish serializeri."""

    city = serializers.CharField(
        max_length=150,
        required=True,
        trim_whitespace=True,
    )
    country = serializers.CharField(
        max_length=150,
        required=True,
        trim_whitespace=True,
    )
    city_native = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=True,
        default="",
        trim_whitespace=True,
    )
    chinese_name = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        default="",
        trim_whitespace=True,
    )
    established_year = serializers.IntegerField(
        required=False,
        allow_null=True,
        default=None,
        min_value=1,
    )
    students_count = serializers.IntegerField(
        required=False,
        allow_null=True,
        default=None,
        min_value=0,
    )
    international_students_count = serializers.IntegerField(
        required=False,
        allow_null=True,
        default=None,
        min_value=0,
    )


class UniversityRevisionUpdateSerializer(serializers.Serializer):
    """Draft revision ma'lumotlarini yangilash serializeri."""

    city = serializers.CharField(
        max_length=150,
        required=False,
        trim_whitespace=True,
        allow_blank=False,
    )
    country = serializers.CharField(
        max_length=150,
        required=False,
        trim_whitespace=True,
        allow_blank=False,
    )
    city_native = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=True,
        trim_whitespace=True,
    )
    chinese_name = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        trim_whitespace=True,
    )
    established_year = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1,
    )
    students_count = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=0,
    )
    international_students_count = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=0,
    )


class UniversityRevisionListSerializer(serializers.ModelSerializer):
    """Revisionlar ro'yxati uchun serializer."""

    class Meta:
        model = UniversityRevision
        fields = [
            "id",
            "university",
            "revision_number",
            "city",
            "country",
            "city_native",
            "chinese_name",
            "established_year",
            "students_count",
            "international_students_count",
            "status",
            "created_by",
            "approved_by",
            "approved_at",
            "published_at",
            "scheduled_publish_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class UniversityRevisionDetailSerializer(serializers.ModelSerializer):
    """Revision tafsilotlari uchun serializer."""

    class Meta:
        model = UniversityRevision
        fields = [
            "id",
            "university",
            "revision_number",
            "city",
            "country",
            "city_native",
            "chinese_name",
            "established_year",
            "students_count",
            "international_students_count",
            "status",
            "created_by",
            "approved_by",
            "approved_at",
            "published_at",
            "scheduled_publish_at",
            "rejection_reason",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields



class UniversityRevisionRejectSerializer(serializers.Serializer):
    """Revisionni rad etish uchun serializer."""

    reason = serializers.CharField(
        required=True,
        max_length=2000,
        trim_whitespace=True,
        allow_blank=False,
    )

