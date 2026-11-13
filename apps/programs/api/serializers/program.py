
from rest_framework import serializers

from apps.programs.models import Program
from apps.programs.services.program_service import (
    resolve_program_translation,
)


class ProgramPublicSerializer(serializers.ModelSerializer):

    title = serializers.CharField(read_only=True)
    subtitle = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    features = serializers.ListField(
        child=serializers.CharField(),
        read_only=True,
    )

    image_url = serializers.ImageField(
        source="image",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = Program

        fields = [
            "id",
            "slug",
            "category",
            "title",
            "subtitle",
            "description",
            "duration",
            "format",
            "pricing_type",
            "price_amount",
            "currency",
            "price_period",
            "features",
            "image_url",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)

        language_code = self.context.get("language_code", "uz")

        translation = resolve_program_translation(
            instance,
            language_code,
        )

        data.update({
            "title": translation.title,
            "subtitle": translation.subtitle,
            "description": translation.description,
            "features": translation.features,
        })

        return data
