
from rest_framework import serializers

from apps.universities.models import UniversityMedia


class UniversityMediaCreateSerializer(serializers.Serializer):
    """Media fayl yuklash serializeri."""

    file = serializers.ImageField(required=True)
    media_type = serializers.ChoiceField(
        choices=UniversityMedia.MediaType.choices,
        required=False,
        default=UniversityMedia.MediaType.GALLERY,
    )
    order = serializers.IntegerField(
        required=False,
        default=0,
        min_value=0,
    )
    caption = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        default="",
        trim_whitespace=True,
    )


class UniversityMediaUpdateSerializer(serializers.Serializer):
    """Media faylni yangilash serializeri."""

    media_type = serializers.ChoiceField(
        choices=UniversityMedia.MediaType.choices,
        required=False,
    )
    order = serializers.IntegerField(
        required=False,
        min_value=0,
    )
    caption = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        trim_whitespace=True,
    )


class UniversityMediaDetailSerializer(serializers.ModelSerializer):
    """Media fayl tafsilotlari serializeri."""

    file_url = serializers.SerializerMethodField()

    class Meta:
        model = UniversityMedia
        fields = [
            "id",
            "university_revision",
            "file",
            "file_url",
            "media_type",
            "order",
            "caption",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_file_url(self, obj) -> str | None:
        if not obj.file:
            return None
        request = self.context.get("request")
        if request is not None:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url
