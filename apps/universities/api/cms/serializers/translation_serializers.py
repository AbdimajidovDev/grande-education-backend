from rest_framework import serializers

from apps.universities.models import (
    UniversityTranslation,
    UniversityTranslationRevision,
)
from apps.universities.constants import SUPPORTED_LANGUAGES


class UniversityTranslationCreateSerializer(serializers.Serializer):
    """Universitet uchun yangi tarjima yaratish serializeri."""

    language_code = serializers.ChoiceField(
        choices=[
            (code, name)
            for code, name in SUPPORTED_LANGUAGES.items()
        ],
        required=True,
    )
    name = serializers.CharField(
        max_length=255,
        required=True,
        trim_whitespace=True,
    )
    slug = serializers.SlugField(
        max_length=255,
        required=True,
    )
    subtitle = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        default="",
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )
    features = serializers.ListField(
        child=serializers.CharField(max_length=150),
        required=False,
        default=list,
    )
    accommodation_info = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )
    admission_note = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )
    seo_title = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        default="",
    )
    seo_description = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )


class UniversityTranslationRevisionCreateSerializer(serializers.Serializer):
    """Mavjud tarjima uchun yangi revision yaratish serializeri."""

    name = serializers.CharField(
        max_length=255,
        required=True,
        trim_whitespace=True,
    )
    slug = serializers.SlugField(
        max_length=255,
        required=True,
    )
    subtitle = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        default="",
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )
    features = serializers.ListField(
        child=serializers.CharField(max_length=150),
        required=False,
        default=list,
    )
    accommodation_info = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )
    admission_note = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )
    seo_title = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        default="",
    )
    seo_description = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )


class UniversityTranslationRevisionUpdateSerializer(serializers.Serializer):
    """Draft tarjima revisionini yangilash serializeri."""

    name = serializers.CharField(
        max_length=255,
        required=False,
        trim_whitespace=True,
    )
    slug = serializers.SlugField(
        max_length=255,
        required=False,
    )
    subtitle = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    features = serializers.ListField(
        child=serializers.CharField(max_length=150),
        required=False,
    )
    accommodation_info = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    admission_note = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    seo_title = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
    )
    seo_description = serializers.CharField(
        required=False,
        allow_blank=True,
    )


class UniversityTranslationListSerializer(serializers.ModelSerializer):
    """Universitet tarjimalari ro'yxati uchun serializer."""

    class Meta:
        model = UniversityTranslation
        fields = [
            "id",
            "university",
            "language_code",
            "slug",
            "published_revision",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class UniversityTranslationRevisionDetailSerializer(
    serializers.ModelSerializer
):
    """Tarjima revisionining to'liq ma'lumotlari uchun serializer."""

    class Meta:
        model = UniversityTranslationRevision
        fields = [
            "id",
            "translation",
            "revision_number",
            "name",
            "slug",
            "subtitle",
            "description",
            "features",
            "accommodation_info",
            "admission_note",
            "seo_title",
            "seo_description",
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



class UniversityTranslationRevisionRejectSerializer(serializers.Serializer):
    reason = serializers.CharField(
        required=True,
        max_length=2000,
        trim_whitespace=True,
        allow_blank=False,
    )
