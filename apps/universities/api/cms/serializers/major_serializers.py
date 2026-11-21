
from rest_framework import serializers

from apps.universities.models import (
    UniversityMajor,
    UniversityMajorTranslation,
)
from apps.universities.constants import SUPPORTED_LANGUAGES


class UniversityMajorTranslationSerializer(serializers.ModelSerializer):
    """Yo'nalish tarjimasi serializeri."""

    class Meta:
        model = UniversityMajorTranslation
        fields = [
            "id",
            "language_code",
            "title",
            "description",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class UniversityMajorTranslationInputSerializer(serializers.Serializer):
    """Yo'nalish yaratishda tarjimalarni qabul qilish uchun serializer."""

    language_code = serializers.ChoiceField(
        choices=[(code, name) for code, name in SUPPORTED_LANGUAGES.items()],
        required=True,
    )
    title = serializers.CharField(
        max_length=255,
        required=True,
        trim_whitespace=True,
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )


class UniversityMajorCreateSerializer(serializers.Serializer):
    """Yangi yo'nalish yaratish serializeri."""

    order = serializers.IntegerField(
        required=False,
        default=0,
        min_value=0,
    )
    is_active = serializers.BooleanField(
        required=False,
        default=True,
    )
    translations = UniversityMajorTranslationInputSerializer(
        many=True,
        required=False,
        default=list,
    )


class UniversityMajorUpdateSerializer(serializers.Serializer):
    """Yo'nalishni tahrirlash serializeri."""

    order = serializers.IntegerField(
        required=False,
        min_value=0,
    )
    is_active = serializers.BooleanField(
        required=False,
    )


class UniversityMajorDetailSerializer(serializers.ModelSerializer):
    """Yo'nalishning to'liq ma'lumotlari serializeri."""

    translations = UniversityMajorTranslationSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = UniversityMajor
        fields = [
            "id",
            "university_revision",
            "order",
            "is_active",
            "translations",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class UniversityMajorTranslationSetSerializer(serializers.Serializer):
    """Yo'nalish uchun muayyan tildagi tarjimani o'rnatish serializeri."""

    language_code = serializers.ChoiceField(
        choices=[(code, name) for code, name in SUPPORTED_LANGUAGES.items()],
        required=True,
    )
    title = serializers.CharField(
        max_length=255,
        required=True,
        trim_whitespace=True,
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )
