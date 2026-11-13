
from rest_framework import serializers

from apps.directions.models import Direction, DirectionTranslation
from apps.inquiries.models import InquiryCategory


class DirectionTranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = DirectionTranslation
        fields = [
            "language_code",
            "number_label",
            "title",
            "summary",
            "tags",
            "goal_text",
            "steps",
            "note",
            "path_text",
        ]

    tags = serializers.ListField(
        child=serializers.CharField(max_length=100, allow_blank=False),
        allow_empty=True,
        max_length=20,
    )

    steps = serializers.ListField(
        child=serializers.CharField(max_length=1000, allow_blank=False),
        allow_empty=False,
        max_length=20,
    )

    def validate(self, attrs):
        required_fields = {
            "number_label",
            "title",
            "summary",
            "tags",
            "goal_text",
            "steps",
            "path_text",
        }

        missing_fields = required_fields - attrs.keys()

        if missing_fields:
            raise serializers.ValidationError({
                field: "This field is required."
                for field in sorted(missing_fields)
            })

        return attrs

    def validate_tags(self, value):
        normalized = [item.strip() for item in value]

        if any(not item for item in normalized):
            raise serializers.ValidationError(
                "Tags cannot contain empty values."
            )

        if len({item.casefold() for item in normalized}) != len(normalized):
            raise serializers.ValidationError(
                "Duplicate tags are not allowed."
            )

        return normalized

    def validate_steps(self, value):
        normalized = [item.strip() for item in value]

        if any(not item for item in normalized):
            raise serializers.ValidationError(
                "Steps cannot contain empty values."
            )

        return normalized


class DirectionAdminSerializer(serializers.ModelSerializer):
    lead_direction_id = serializers.PrimaryKeyRelatedField(
        source="inquiry_category",
        queryset=InquiryCategory.objects.filter(is_active=True),
        allow_null=True,
        required=False,
    )

    translations = DirectionTranslationSerializer(
        many=True,
        required=True,
        max_length=6,
    )

    class Meta:
        model = Direction
        fields = [
            "id",
            "order",
            "chinese_char",
            "lead_direction_id",
            "is_active",
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
            translation["language_code"]
            for translation in value
        ]

        if len(language_codes) != len(set(language_codes)):
            raise serializers.ValidationError(
                "Duplicate language translations are not allowed."
            )

        if len(language_codes) > 6:
            raise serializers.ValidationError(
                "Maximum 6 translations are allowed."
            )

        if (self.instance is None or not self.partial) and "uz" not in language_codes:
            raise serializers.ValidationError(
                "Uzbek translation is required when creating a direction."
            )

        return value

    def validate_chinese_char(self, value):
        return value.strip()

    def validate(self, attrs):
        if (
            self.instance is None
            and "inquiry_category" not in attrs
        ):
            attrs["inquiry_category"] = None

        return attrs


class DirectionPublicSerializer(serializers.ModelSerializer):
    number_label = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    summary = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    goal_text = serializers.SerializerMethodField()
    steps = serializers.SerializerMethodField()
    note = serializers.SerializerMethodField()
    path_text = serializers.SerializerMethodField()

    lead_direction_id = serializers.IntegerField(
        source="inquiry_category_id",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = Direction
        fields = [
            "id",
            "order",
            "number_label",
            "chinese_char",
            "title",
            "summary",
            "tags",
            "goal_text",
            "steps",
            "note",
            "path_text",
            "lead_direction_id",
        ]

    def get_translation(self, obj):
        if not hasattr(obj, "_resolved_translation"):
            from apps.directions.selectors import (
                resolve_direction_translation,
            )

            language_code = self.context.get("language_code", "uz")

            obj._resolved_translation = resolve_direction_translation(
                obj,
                language_code,
            )

        return obj._resolved_translation

    def get_number_label(self, obj):
        return self.get_translation(obj).number_label

    def get_title(self, obj):
        return self.get_translation(obj).title

    def get_summary(self, obj):
        return self.get_translation(obj).summary

    def get_tags(self, obj):
        return self.get_translation(obj).tags

    def get_goal_text(self, obj):
        return self.get_translation(obj).goal_text

    def get_steps(self, obj):
        return self.get_translation(obj).steps

    def get_note(self, obj):
        return self.get_translation(obj).note

    def get_path_text(self, obj):
        return self.get_translation(obj).path_text
