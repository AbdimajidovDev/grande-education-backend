from rest_framework import serializers

from apps.universities.models import University, UniversityRevision


class UniversityCreateSerializer(serializers.Serializer):
    """Universitet yaratish uchun serializer."""

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


class UniversityListSerializer(serializers.ModelSerializer):
    """Universitetlar ro'yxati uchun serializer."""

    class Meta:
        model = University
        fields = [
            "id",
            "status",
            "published_revision",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class UniversityDetailSerializer(serializers.ModelSerializer):
    """Universitet tafsilotlari uchun serializer."""

    class Meta:
        model = University
        fields = [
            "id",
            "status",
            "published_revision",
            "created_by",
            "updated_by",
            "rejection_reason",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields