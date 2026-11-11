
from rest_framework import serializers

from apps.universities.models import FAQTranslation


class PublicFAQSerializer(serializers.ModelSerializer):
    """Public FAQ savol-javoblari uchun."""

    id = serializers.UUIDField(
        source="faq.id",
        read_only=True,
    )
    order = serializers.IntegerField(
        source="faq.order",
        read_only=True,
    )
    question = serializers.CharField(
        source="published_revision.question",
        read_only=True,
    )
    answer = serializers.CharField(
        source="published_revision.answer",
        read_only=True,
    )

    class Meta:
        model = FAQTranslation
        fields = [
            "id",
            "language_code",
            "order",
            "question",
            "answer",
        ]
        read_only_fields = fields
