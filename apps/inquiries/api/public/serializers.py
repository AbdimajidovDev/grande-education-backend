
from rest_framework import serializers

from apps.inquiries.models import Inquiry, InquiryCategory
from apps.universities.models import University


class InquiryConsentSerializer(serializers.Serializer):
    accepted = serializers.BooleanField()
    version = serializers.CharField(max_length=20)

    def validate_accepted(self, value):
        if not value:
            raise serializers.ValidationError(
                "Rozilik berishingiz kerak."
            )
        return value

    def validate_version(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Rozilik versiyasi ko'rsatilishi shart."
            )

        return value


class InquiryCreateSerializer(serializers.Serializer):
    name = serializers.CharField(
        source="full_name",
        max_length=255,
    )
    phone = serializers.CharField(
        source="phone_number",
        max_length=20,
    )
    email = serializers.EmailField(
        required=False,
        allow_blank=True,
    )

    category = serializers.PrimaryKeyRelatedField(
        queryset=InquiryCategory.objects.filter(is_active=True),
    )

    university = serializers.PrimaryKeyRelatedField(
        queryset=University.objects.all(),
        required=False,
        allow_null=True,
    )

    contactMethod = serializers.ChoiceField(
        source="contact_method",
        choices=Inquiry.ContactMethod.choices,
    )

    message = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    consent = InquiryConsentSerializer()

    locale = serializers.CharField(
        max_length=10,
        default="uz",
    )

    idempotencyKey = serializers.UUIDField(
        source="idempotency_key",
    )

    def validate_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Ism va familiya kiritilishi shart."
            )

        return value

    def validate_phone(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Telefon raqami kiritilishi shart."
            )

        return value

    def validate_locale(self, value):
        value = value.strip().lower()

        if not value:
            raise serializers.ValidationError(
                "Til kodi kiritilishi shart."
            )

        return value

    def validate(self, attrs):
        consent = attrs.pop("consent")

        attrs["consent_accepted"] = consent["accepted"]
        attrs["consent_version"] = consent["version"]

        attrs.setdefault("email", "")
        attrs.setdefault("message", "")
        attrs.setdefault("university", None)

        return attrs


class InquiryCategorySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    slug = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField()
