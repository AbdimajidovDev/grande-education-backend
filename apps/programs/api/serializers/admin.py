from django.db import transaction
from rest_framework import serializers

from apps.programs.models import Program, ProgramTranslation


class ProgramTranslationAdminSerializer(serializers.ModelSerializer):

    class Meta:
        model = ProgramTranslation
        fields = [
            "language_code",
            "title",
            "subtitle",
            "description",
            "features",
        ]


class ProgramAdminSerializer(serializers.ModelSerializer):

    translations = ProgramTranslationAdminSerializer(
        many=True,
        required=False,
    )

    class Meta:
        model = Program
        fields = [
            "id",
            "slug",
            "category",
            "duration",
            "format",
            "pricing_type",
            "price_amount",
            "currency",
            "price_period",
            "image",
            "order",
            "is_published",
            "translations",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]

    def validate_translations(self, value):
        language_codes = [
            item["language_code"]
            for item in value
        ]

        if len(language_codes) != len(set(language_codes)):
            raise serializers.ValidationError(
                "Each language can only have one translation."
            )

        return value

    def validate(self, attrs):
        instance = self.instance

        pricing_type = attrs.get(
            "pricing_type",
            getattr(instance, "pricing_type", None),
        )

        price_amount = attrs.get(
            "price_amount",
            getattr(instance, "price_amount", None),
        )

        price_period = attrs.get(
            "price_period",
            getattr(instance, "price_period", None),
        )

        if pricing_type == Program.PricingType.FREE:
            attrs["price_amount"] = None
            attrs["price_period"] = None

        elif pricing_type == Program.PricingType.PAID:
            if price_amount is None or price_amount <= 0:
                raise serializers.ValidationError({
                    "price_amount": "Paid programs require a positive price."
                })

            if not price_period:
                raise serializers.ValidationError({
                    "price_period": "Paid programs require a price period."
                })

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        translations_data = validated_data.pop("translations", [])

        program = Program.objects.create(**validated_data)

        ProgramTranslation.objects.bulk_create([
            ProgramTranslation(
                program=program,
                **translation_data,
            )
            for translation_data in translations_data
        ])

        return program

    @transaction.atomic
    def update(self, instance, validated_data):
        translations_data = validated_data.pop("translations", [])

        instance = super().update(instance, validated_data)

        for translation_data in translations_data:
            language_code = translation_data.pop("language_code")

            ProgramTranslation.objects.update_or_create(
                program=instance,
                language_code=language_code,
                defaults=translation_data,
            )

        return instance
