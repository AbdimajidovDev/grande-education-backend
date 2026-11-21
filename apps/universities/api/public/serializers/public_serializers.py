
from rest_framework import serializers


class PublicUniversityBaseSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    city = serializers.CharField(
        source="published_revision.city",
        read_only=True,
    )
    city_native = serializers.CharField(
        source="published_revision.city_native",
        read_only=True,
    )
    country = serializers.CharField(
        source="published_revision.country",
        read_only=True,
    )
    chinese_name = serializers.CharField(
        source="published_revision.chinese_name",
        read_only=True,
    )
    established_year = serializers.IntegerField(
        source="published_revision.established_year",
        read_only=True,
    )
    students_count = serializers.IntegerField(
        source="published_revision.students_count",
        read_only=True,
    )
    international_students_count = serializers.IntegerField(
        source="published_revision.international_students_count",
        read_only=True,
    )

    name = serializers.SerializerMethodField()
    slug = serializers.SerializerMethodField()
    subtitle = serializers.SerializerMethodField()
    language_code = serializers.SerializerMethodField()
    logo = serializers.SerializerMethodField()
    cover = serializers.SerializerMethodField()

    class Meta:
        fields = [
            "id",
            "city",
            "city_native",
            "country",
            "chinese_name",
            "established_year",
            "students_count",
            "international_students_count",
            "name",
            "slug",
            "subtitle",
            "language_code",
            "logo",
            "cover",
        ]

    def get_public_translation(self, obj):
        requested_language = (
            self.context.get("language_code") or "uz"
        ).strip().lower()

        translations = getattr(obj, "public_translations", None)
        if translations is None:
            return None

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
        if translation is None or not translation.published_revision:
            return None
        return translation.published_revision.name

    def get_slug(self, obj):
        translation = self.get_public_translation(obj)
        if translation is None or not translation.published_revision:
            return None
        return translation.published_revision.slug

    def get_subtitle(self, obj):
        translation = self.get_public_translation(obj)
        if translation is None or not translation.published_revision:
            return ""
        return getattr(translation.published_revision, "subtitle", "")

    def get_language_code(self, obj):
        translation = self.get_public_translation(obj)
        if translation is None:
            return None
        return translation.language_code

    def _get_media_url(self, obj, media_type: str) -> str | None:
        if not obj.published_revision:
            return None
        media = (
            obj.published_revision.media_items
            .filter(media_type=media_type)
            .order_by("order", "created_at")
            .first()
        )
        if not media or not media.file:
            return None
        request = self.context.get("request")
        if request is not None:
            return request.build_absolute_uri(media.file.url)
        return media.file.url

    def get_logo(self, obj):
        return self._get_media_url(obj, "logo")

    def get_cover(self, obj):
        return self._get_media_url(obj, "cover")


class PublicUniversityListSerializer(PublicUniversityBaseSerializer):
    pass


class PublicUniversityDetailSerializer(PublicUniversityBaseSerializer):
    description = serializers.SerializerMethodField()
    features = serializers.SerializerMethodField()
    accommodation_info = serializers.SerializerMethodField()
    admission_note = serializers.SerializerMethodField()
    gallery = serializers.SerializerMethodField()
    majors = serializers.SerializerMethodField()
    seo_title = serializers.SerializerMethodField()
    seo_description = serializers.SerializerMethodField()

    class Meta(PublicUniversityBaseSerializer.Meta):
        fields = PublicUniversityBaseSerializer.Meta.fields + [
            "description",
            "features",
            "accommodation_info",
            "admission_note",
            "gallery",
            "majors",
            "seo_title",
            "seo_description",
        ]

    def get_description(self, obj):
        translation = self.get_public_translation(obj)
        if translation is None or not translation.published_revision:
            return None
        return translation.published_revision.description

    def get_features(self, obj):
        translation = self.get_public_translation(obj)
        if translation is None or not translation.published_revision:
            return []
        return getattr(translation.published_revision, "features", [])

    def get_accommodation_info(self, obj):
        translation = self.get_public_translation(obj)
        if translation is None or not translation.published_revision:
            return ""
        return getattr(translation.published_revision, "accommodation_info", "")

    def get_admission_note(self, obj):
        translation = self.get_public_translation(obj)
        if translation is None or not translation.published_revision:
            return ""
        return getattr(translation.published_revision, "admission_note", "")

    def get_gallery(self, obj):
        if not obj.published_revision:
            return []
        gallery_items = (
            obj.published_revision.media_items
            .filter(media_type="gallery")
            .order_by("order", "created_at")
        )
        request = self.context.get("request")
        result = []
        for item in gallery_items:
            if not item.file:
                continue
            url = request.build_absolute_uri(item.file.url) if request else item.file.url
            result.append({
                "id": str(item.id),
                "url": url,
                "caption": item.caption,
                "order": item.order,
            })
        return result

    def get_majors(self, obj):
        if not obj.published_revision:
            return []
        majors = (
            obj.published_revision.majors
            .filter(is_active=True)
            .prefetch_related("translations")
            .order_by("order", "created_at")
        )
        requested_language = (
            self.context.get("language_code") or "uz"
        ).strip().lower()

        result = []
        for major in majors:
            translations = list(major.translations.all())
            trans = next((t for t in translations if t.language_code == requested_language), None)
            if trans is None:
                trans = next((t for t in translations if t.language_code == "uz"), None)
            if trans is None and translations:
                trans = translations[0]

            result.append({
                "id": str(major.id),
                "order": major.order,
                "title": trans.title if trans else "",
                "description": trans.description if trans else "",
            })
        return result

    def get_seo_title(self, obj):
        translation = self.get_public_translation(obj)
        if translation is None or not translation.published_revision:
            return None
        return translation.published_revision.seo_title

    def get_seo_description(self, obj):
        translation = self.get_public_translation(obj)
        if translation is None or not translation.published_revision:
            return None
        return translation.published_revision.seo_description
