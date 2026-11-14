from rest_framework import serializers

from apps.education_content.models import (
    HybridTeacher,
    HybridTeacherTranslation,
    LearningComponent,
    LearningComponentTranslation,
)
from .fields import MultipartJSONListField
from drf_spectacular.utils import extend_schema_field

# =========================================================
# Shared validation
# =========================================================

def validate_translations(translations, *, require_uz=True):
    language_codes = [
        item["language_code"]
        for item in translations
    ]

    if len(language_codes) != len(set(language_codes)):
        raise serializers.ValidationError(
            "Duplicate language translations are not allowed."
        )

    if require_uz and "uz" not in language_codes:
        raise serializers.ValidationError(
            "Uzbek translation is required."
        )


def resolve_translation(instance, language_code):
    translations = instance.prefetched_translations

    return (
        next(
            (
                item for item in translations
                if item.language_code == language_code
            ),
            None,
        )
        or next(
            (
                item for item in translations
                if item.language_code == "uz"
            ),
            None,
        )
    )


# =========================================================
# Hybrid Teacher
# =========================================================

class HybridTeacherTranslationSerializer(serializers.ModelSerializer):
    features = serializers.ListField(
        child=serializers.CharField(
            allow_blank=False,
            trim_whitespace=True,
        ),
        allow_empty=True,
    )

    class Meta:
        model = HybridTeacherTranslation
        fields = (
            "language_code",
            "title",
            "subtitle",
            "features",
        )


class HybridTeacherAdminSerializer(serializers.ModelSerializer):
    translations = extend_schema_field(
        HybridTeacherTranslationSerializer(many=True)
    )(
        MultipartJSONListField(
            serializer_class=HybridTeacherTranslationSerializer,
            required=True,
        )
    )

    class Meta:
        model = HybridTeacher
        fields = (
            "id",
            "badge",
            "chinese_tag",
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


class HybridTeacherPublicSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    subtitle = serializers.SerializerMethodField()
    features = serializers.SerializerMethodField()

    class Meta:
        model = HybridTeacher
        fields = (
            "id",
            "badge",
            "chinese_tag",
            "image",
            "title",
            "subtitle",
            "features",
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

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_features(self, obj):
        translation = self._get_translation(obj)
        return translation.features if translation else []


# =========================================================
# Learning Component
# =========================================================

class LearningComponentTranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningComponentTranslation
        fields = (
            "language_code",
            "title",
            "description",
        )


class LearningComponentAdminSerializer(serializers.ModelSerializer):
    translations = extend_schema_field(
        LearningComponentTranslationSerializer(many=True)
    )(
        MultipartJSONListField(
            serializer_class=LearningComponentTranslationSerializer,
            required=True,
        )
    )

    class Meta:
        model = LearningComponent
        fields = (
            "id",
            "icon",
            "chinese_char",
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


class LearningComponentPublicSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()

    class Meta:
        model = LearningComponent
        fields = (
            "id",
            "icon",
            "chinese_char",
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
    def get_title(self, obj):
        translation = self._get_translation(obj)
        return translation.title if translation else None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_description(self, obj):
        translation = self._get_translation(obj)
        return translation.description if translation else None
