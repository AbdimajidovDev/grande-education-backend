
from rest_framework import serializers


class PublicUniversityBaseSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    city = serializers.CharField(
        source="published_revision.city",
        read_only=True,
    )
    country = serializers.CharField(
        source="published_revision.country",
        read_only=True,
    )

    name = serializers.SerializerMethodField()
    slug = serializers.SerializerMethodField()
    language_code = serializers.SerializerMethodField()

    class Meta:
        fields = [
            "id",
            "city",
            "country",
            "name",
            "slug",
            "language_code",
        ]

    def get_public_translation(self, obj):
        requested_language = (
            self.context.get("language_code") or "uz"
        ).strip().lower()

        translations = obj.public_translations

        # Avval so'ralgan tilni qidiramiz.
        translation = next(
            (
                item
                for item in translations
                if item.language_code == requested_language
            ),
            None,
        )

        # So'ralgan tilda tarjima bo'lmasa, Uzbek tiliga fallback.
        if translation is None:
            translation = next(
                (
                    item
                    for item in translations
                    if item.language_code == "uz"
                ),
                None,
            )

        return translation

    def get_name(self, obj):
        translation = self.get_public_translation(obj)

        if translation is None:
            return None

        return translation.published_revision.name

    def get_slug(self, obj):
        translation = self.get_public_translation(obj)

        if translation is None:
            return None

        return translation.published_revision.slug

    def get_language_code(self, obj):
        translation = self.get_public_translation(obj)

        if translation is None:
            return None

        return translation.language_code


class PublicUniversityListSerializer(PublicUniversityBaseSerializer):
    pass


class PublicUniversityDetailSerializer(PublicUniversityBaseSerializer):
    description = serializers.SerializerMethodField()
    seo_title = serializers.SerializerMethodField()
    seo_description = serializers.SerializerMethodField()

    class Meta(PublicUniversityBaseSerializer.Meta):
        fields = PublicUniversityBaseSerializer.Meta.fields + [
            "description",
            "seo_title",
            "seo_description",
        ]

    def get_description(self, obj):
        translation = self.get_public_translation(obj)

        if translation is None:
            return None

        return translation.published_revision.description

    def get_seo_title(self, obj):
        translation = self.get_public_translation(obj)

        if translation is None:
            return None

        return translation.published_revision.seo_title

    def get_seo_description(self, obj):
        translation = self.get_public_translation(obj)

        if translation is None:
            return None

        return translation.published_revision.seo_description
