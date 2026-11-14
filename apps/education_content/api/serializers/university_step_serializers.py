from rest_framework import serializers

from apps.education_content.models import (
    UniversityStep,
    UniversityStepPage,
    UniversityStepPageTranslation,
    UniversityStepTranslation,
)

from .hybrid_serializers import (
    validate_translations,
    resolve_translation,
)
from .fields import MultipartJSONListField
from drf_spectacular.utils import extend_schema_field


# =========================================================
# Translation serializers
# =========================================================

class UniversityStepPageTranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = UniversityStepPageTranslation
        fields = (
            "language_code",
            "title",
            "subtitle",
        )


class UniversityStepTranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = UniversityStepTranslation
        fields = (
            "language_code",
            "action_verb",
            "title",
            "description",
        )


# =========================================================
# Admin serializers
# =========================================================

class UniversityStepAdminSerializer(serializers.ModelSerializer):
    translations = extend_schema_field(
        UniversityStepTranslationSerializer(many=True)
    )(
        MultipartJSONListField(
            serializer_class=UniversityStepTranslationSerializer,
            required=True,
        )
    )

    class Meta:
        model = UniversityStep
        fields = (
            "id",
            "page",
            "step_number",
            "dazhi_numeral",
            "chinese_char",
            "pinyin",
            "chinese_concept",
            "image",
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

    def validate_translations(self, value):
        validate_translations(
            value,
            require_uz=(
                self.instance is None
                or not self.partial
            ),
        )
        return value


class UniversityStepPageAdminSerializer(serializers.ModelSerializer):
    translations = extend_schema_field(
        UniversityStepPageTranslationSerializer(many=True)
    )(
        MultipartJSONListField(
            serializer_class=UniversityStepPageTranslationSerializer,
            required=True,
        )
    )

    class Meta:
        model = UniversityStepPage
        fields = (
            "id",
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

    def validate_translations(self, value):
        validate_translations(
            value,
            require_uz=(
                self.instance is None
                or not self.partial
            ),
        )
        return value

    def validate_steps(self, value):
        step_numbers = [
            item["step_number"]
            for item in value
        ]

        if len(step_numbers) != len(set(step_numbers)):
            raise serializers.ValidationError(
                "Duplicate step numbers are not allowed."
            )

        if len(value) > 5:
            raise serializers.ValidationError(
                "A maximum of five steps is allowed."
            )

        return value


# =========================================================
# Public serializers
# =========================================================

class UniversityStepPublicSerializer(serializers.ModelSerializer):
    action_verb = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()

    class Meta:
        model = UniversityStep
        fields = (
            "id",
            "step_number",
            "dazhi_numeral",
            "chinese_char",
            "pinyin",
            "chinese_concept",
            "image",
            "action_verb",
            "title",
            "description",
        )

    def _get_translation(self, obj):
        language_code = self.context.get(
            "language_code",
            "uz",
        )
        return resolve_translation(obj, language_code)

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_action_verb(self, obj):
        translation = self._get_translation(obj)
        return translation.action_verb if translation else None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_title(self, obj):
        translation = self._get_translation(obj)
        return translation.title if translation else None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_description(self, obj):
        translation = self._get_translation(obj)
        return translation.description if translation else None


class UniversityStepPagePublicSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    subtitle = serializers.SerializerMethodField()
    steps = UniversityStepPublicSerializer(
        source="prefetched_steps",
        many=True,
    )

    class Meta:
        model = UniversityStepPage
        fields = (
            "title",
            "subtitle",
            "steps",
        )

    def _get_translation(self, obj):
        language_code = self.context.get(
            "language_code",
            "uz",
        )
        return resolve_translation(obj, language_code)

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_title(self, obj):
        translation = self._get_translation(obj)
        return translation.title if translation else None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_subtitle(self, obj):
        translation = self._get_translation(obj)
        return translation.subtitle if translation else None
