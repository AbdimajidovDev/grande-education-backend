
from rest_framework import serializers

from apps.partners.models import Partner


class PartnerPublicSerializer(serializers.ModelSerializer):
    logo_url = serializers.ImageField(
        source="logo",
        read_only=True,
    )

    class Meta:
        model = Partner
        fields = [
            "id",
            "name",
            "description",
            "logo_url",
            "website",
        ]


class PartnerAdminSerializer(serializers.ModelSerializer):
    logo_url = serializers.ImageField(
        source="logo",
        read_only=True,
    )

    class Meta:
        model = Partner
        fields = [
            "id",
            "name",
            "description",
            "logo",
            "logo_url",
            "website",
            "order",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]
