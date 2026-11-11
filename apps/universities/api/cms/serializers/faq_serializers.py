
from rest_framework import serializers

from apps.universities.models import (
    FAQ,
    FAQTranslation,
    FAQTranslationRevision,
)


class FAQCreateSerializer(serializers.ModelSerializer):
    """Yangi FAQ yaratish uchun."""

    class Meta:
        model = FAQ
        fields = ["order"]


class FAQUpdateSerializer(serializers.ModelSerializer):
    """FAQ tartibi va faollik holatini yangilash uchun."""

    class Meta:
        model = FAQ
        fields = ["order", "is_active"]
        extra_kwargs = {
            "order": {"required": False, "min_value": 0},
            "is_active": {"required": False},
        }

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(
                "Kamida bitta maydon yuborilishi kerak."
            )
        return attrs


class FAQListSerializer(serializers.ModelSerializer):
    """FAQ ro'yxati uchun."""

    class Meta:
        model = FAQ
        fields = [
            "id",
            "order",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class FAQTranslationCreateSerializer(serializers.Serializer):
    """FAQ uchun yangi tarjima yaratish so'rovi."""

    language_code = serializers.CharField(max_length=10)
    question = serializers.CharField(max_length=500)
    answer = serializers.CharField()


class FAQTranslationListSerializer(serializers.ModelSerializer):
    """FAQ tarjimalari ro'yxati uchun."""

    class Meta:
        model = FAQTranslation
        fields = [
            "id",
            "language_code",
            "published_revision",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class FAQRevisionCreateSerializer(serializers.Serializer):
    """Yangi FAQ revision yaratish uchun."""

    question = serializers.CharField(max_length=500)
    answer = serializers.CharField()


class FAQRevisionUpdateSerializer(serializers.ModelSerializer):
    """DRAFT FAQ revisionini yangilash uchun."""

    class Meta:
        model = FAQTranslationRevision
        fields = ["question", "answer"]
        extra_kwargs = {
            "question": {"required": False},
            "answer": {"required": False},
        }

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(
                "Kamida bitta maydon yuborilishi kerak."
            )
        return attrs


class FAQRevisionListSerializer(serializers.ModelSerializer):
    """FAQ revisionlari tarixi uchun."""

    class Meta:
        model = FAQTranslationRevision
        fields = [
            "id",
            "revision_number",
            "question",
            "answer",
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

