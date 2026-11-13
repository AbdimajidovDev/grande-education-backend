import json

from PIL import Image, UnidentifiedImageError
from pillow_heif import register_heif_opener
from rest_framework import serializers

from apps.teachers.models import Teacher, TeacherTranslation
from apps.teachers.selectors import resolve_teacher_translation


register_heif_opener()


MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB

ALLOWED_IMAGE_FORMATS = {
    "JPEG",
    "PNG",
    "WEBP",
    "HEIF",
}

# Translation limits
MAX_TRANSLATIONS = 6
MAX_SKILLS = 20
MAX_SKILL_LENGTH = 80
MAX_BIO_LENGTH = 5000


class TeacherTranslationSerializer(serializers.ModelSerializer):
    skills = serializers.ListField(
        child=serializers.CharField(
            max_length=MAX_SKILL_LENGTH,
            allow_blank=False,
            trim_whitespace=True,
        ),
        allow_empty=True,
        max_length=MAX_SKILLS,
    )

    role = serializers.CharField(
        max_length=255,
        trim_whitespace=True,
    )

    experience = serializers.CharField(
        max_length=255,
        trim_whitespace=True,
    )

    bio = serializers.CharField(
        max_length=MAX_BIO_LENGTH,
        trim_whitespace=True,
    )

    class Meta:
        model = TeacherTranslation
        fields = [
            "language_code",
            "role",
            "experience",
            "bio",
            "skills",
        ]

    def validate_role(self, value):
        if not value:
            raise serializers.ValidationError(
                "Lavozim bo'sh bo'lishi mumkin emas."
            )
        return value

    def validate_experience(self, value):
        if not value:
            raise serializers.ValidationError(
                "Tajriba maydoni bo'sh bo'lishi mumkin emas."
            )
        return value

    def validate_bio(self, value):
        if not value:
            raise serializers.ValidationError(
                "Biografiya bo'sh bo'lishi mumkin emas."
            )
        return value

    def validate_skills(self, value):
        normalized = [skill.casefold() for skill in value]

        if len(normalized) != len(set(normalized)):
            raise serializers.ValidationError(
                "Ko'nikmalar ro'yxatida takroriy qiymatlar bo'lmasligi kerak."
            )

        return value


class TeacherPublicSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    experience = serializers.SerializerMethodField()
    bio = serializers.SerializerMethodField()
    skills = serializers.SerializerMethodField()

    photo_url = serializers.ImageField(
        source="photo",
        read_only=True,
    )

    class Meta:
        model = Teacher
        fields = [
            "id",
            "full_name",
            "role",
            "experience",
            "bio",
            "photo_url",
            "skills",
        ]

    def _get_translation(self, obj):
        language_code = self.context.get("language_code", "uz")

        # Bitta teacher uchun tarjima obyektini qayta-qayta
        # resolve qilishning oldini olamiz.
        cache = self.context.setdefault(
            "_teacher_translation_cache",
            {},
        )

        if obj.pk not in cache:
            cache[obj.pk] = resolve_teacher_translation(
                obj,
                language_code,
            )

        return cache[obj.pk]

    def get_role(self, obj):
        return self._get_translation(obj).role

    def get_experience(self, obj):
        return self._get_translation(obj).experience

    def get_bio(self, obj):
        return self._get_translation(obj).bio

    def get_skills(self, obj):
        return self._get_translation(obj).skills


class TeacherAdminSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(
        max_length=255,
        min_length=2,
        trim_whitespace=True,
    )

    photo = serializers.ImageField(
        allow_empty_file=False,
    )

    translations = TeacherTranslationSerializer(
        many=True,
        required=True,
        max_length=MAX_TRANSLATIONS,
    )

    photo_url = serializers.ImageField(
        source="photo",
        read_only=True,
    )

    class Meta:
        model = Teacher
        fields = [
            "id",
            "full_name",
            "photo",
            "photo_url",
            "order",
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

    def to_internal_value(self, data):
        """
        JSON va multipart/form-data so'rovlarida
        translations maydonini bir xil formatga keltiradi.
        """

        if hasattr(data, "getlist"):
            normalized_data = {
                key: data.getlist(key)[-1]
                for key in data
                if data.getlist(key)
            }
        else:
            normalized_data = data.copy()

        translations = normalized_data.get("translations")

        if isinstance(translations, str):
            try:
                translations = json.loads(translations)
            except (json.JSONDecodeError, TypeError):
                raise serializers.ValidationError({
                    "translations": (
                        "Tarjimalar to'g'ri JSON formatida bo'lishi kerak."
                    )
                })

            normalized_data["translations"] = translations

        return super().to_internal_value(normalized_data)

    def validate_full_name(self, value):
        value = " ".join(value.split())

        if len(value) < 2:
            raise serializers.ValidationError(
                "O'qituvchi ismi kamida 2 ta belgidan iborat bo'lishi kerak."
            )

        return value

    def validate_photo(self, value):
        if value.size > MAX_IMAGE_SIZE:
            raise serializers.ValidationError(
                "Rasm hajmi 5 MB dan oshmasligi kerak."
            )

        try:
            value.seek(0)

            with Image.open(value) as image:
                if image.format not in ALLOWED_IMAGE_FORMATS:
                    raise serializers.ValidationError(
                        "Faqat JPEG, PNG, WebP va HEIC formatidagi rasmlar qabul qilinadi."
                    )

                image.verify()

        except serializers.ValidationError:
            raise

        except (
                UnidentifiedImageError,
                Image.DecompressionBombError,
                OSError,
                ValueError,
        ):
            raise serializers.ValidationError(
                "Yuklangan fayl haqiqiy yoki yaroqli rasm emas."
            )

        finally:
            value.seek(0)

        return value

    def validate_translations(self, translations):
        language_codes = [
            translation["language_code"]
            for translation in translations
        ]

        if len(language_codes) != len(set(language_codes)):
            raise serializers.ValidationError(
                "Bir til uchun faqat bitta tarjima yuborish mumkin."
            )

        if self.instance is None and "uz" not in language_codes:
            raise serializers.ValidationError(
                "Yangi o'qituvchi uchun o'zbekcha tarjima majburiy."
            )

        return translations
