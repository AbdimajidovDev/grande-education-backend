from apps.site_settings.selectors import (
    resolve_site_stat_translation,
)
from rest_framework import serializers

from apps.site_settings.models import (
    SiteStat,
    SiteStatTranslation,
)


class SiteStatTranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteStatTranslation
        fields = (
            "language_code",
            "label",
            "hint",
        )

    def validate_label(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Translation label cannot be empty."
            )

        return value

    def validate_hint(self, value):
        return value.strip()


class SiteStatAdminSerializer(serializers.ModelSerializer):
    translations = SiteStatTranslationSerializer(
        many=True,
        required=True,
    )

    class Meta:
        model = SiteStat
        fields = (
            "id",
            "number",
            "is_counter",
            "order",
            "is_active",
            "translations",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )

    def validate_number(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Number cannot be empty."
            )

        if not all(
            char.isalnum()
            or char.isspace()
            or char in "%.,–—+-/()"
            for char in value
        ):
            raise serializers.ValidationError(
                "Number contains unsupported characters."
            )

        return value

    def validate_translations(self, value):
        if not value:
            raise serializers.ValidationError(
                "At least one translation is required."
            )

        language_codes = [
            item["language_code"]
            for item in value
        ]

        if len(language_codes) != len(set(language_codes)):
            raise serializers.ValidationError(
                "Duplicate language translations are not allowed."
            )

        return value

    def validate(self, attrs):
        translations = attrs.get("translations")

        requires_uzbek = (
            self.instance is None
            or not self.partial
        )

        if requires_uzbek and translations is not None:
            language_codes = {
                item["language_code"]
                for item in translations
            }

            if "uz" not in language_codes:
                raise serializers.ValidationError({
                    "translations": (
                        "Uzbek translation is required."
                    )
                })

        return attrs




class SiteStatPublicSerializer(serializers.ModelSerializer):
    label = serializers.SerializerMethodField()
    hint = serializers.SerializerMethodField()

    class Meta:
        model = SiteStat
        fields = (
            "number",
            "label",
            "hint",
            "is_counter",
        )

    def get_translation(self, obj):
        language_code = self.context.get("language_code", "uz")
        return resolve_site_stat_translation(
            obj,
            language_code,
        )

    def get_label(self, obj):
        translation = self.get_translation(obj)
        return translation.label if translation else ""

    def get_hint(self, obj):
        translation = self.get_translation(obj)
        return translation.hint if translation else ""

