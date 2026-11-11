from django.db.models import Exists, F, OuterRef, Prefetch, QuerySet

from apps.universities.models import (
    University,
    UniversityTranslation,
    UniversityTranslationRevision, UniversityRevision,
)
from apps.universities.constants import SUPPORTED_LANGUAGES


class UniversitySelector:
    """Universitet ma'lumotlarini o'qish uchun selector."""

    @staticmethod
    def get_university_queryset() -> QuerySet:
        """Barcha universitetlarni optimallashtirilgan queryset orqali oladi."""

        return (
            University.objects
            .select_related(
                "published_revision",
                "created_by",
                "updated_by",
            )
            .order_by("-created_at")
        )

    @staticmethod
    def get_university_by_id(university_id) -> University | None:
        """ID orqali universitetni oladi."""

        return (
            UniversitySelector.get_university_queryset()
            .filter(pk=university_id)
            .first()
        )

    @staticmethod
    def get_university_by_id_for_update(
        university_id,
    ) -> University | None:
        """O'zgartirishdan oldin bloklangan universitetni oladi."""

        return (
            University.objects
            .select_for_update()
            .select_related("published_revision")
            .filter(pk=university_id)
            .first()
        )

    @classmethod
    def get_public_university_queryset(cls, language_code="uz"):
        language_code = (language_code or "uz").strip().lower()

        if language_code not in SUPPORTED_LANGUAGES:
            language_code = "uz"

        # Universitetda PUBLISHED Uzbek tarjimasi mavjudligini tekshirish.
        published_uz_translation = UniversityTranslation.objects.filter(
            university_id=OuterRef("pk"),
            language_code="uz",
            published_revision__isnull=False,
            published_revision__status=(
                UniversityTranslationRevision.Status.PUBLISHED
            ),
            published_revision__translation_id=F("pk"),
        )

        # Kerakli tillardagi PUBLISHED tarjimalarni yuklash.
        translations_queryset = (
            UniversityTranslation.objects
            .filter(
                language_code__in={language_code, "uz"},
                published_revision__isnull=False,
                published_revision__status=(
                    UniversityTranslationRevision.Status.PUBLISHED
                ),
                published_revision__translation_id=F("pk"),
            )
            .select_related("published_revision")
        )

        return (
            University.objects
            .filter(
                status=University.Status.PUBLISHED,
                published_revision__status=UniversityRevision.Status.PUBLISHED,
            )
            .filter(Exists(published_uz_translation))
            .select_related("published_revision")
            .prefetch_related(
                Prefetch(
                    "translations",
                    queryset=translations_queryset,
                    to_attr="public_translations",
                )
            )
            .order_by("-updated_at")
        )



    @classmethod
    def get_public_university_by_slug(cls, slug, language_code="uz"):
        language_code = (language_code or "uz").strip().lower()

        if language_code not in SUPPORTED_LANGUAGES:
            language_code = "uz"

        languages_to_try = (
            [language_code, "uz"]
            if language_code != "uz"
            else ["uz"]
        )

        for current_language in languages_to_try:
            queryset = cls.get_public_university_queryset(
                language_code=current_language,
            )

            university = (
                queryset
                .filter(
                    translations__language_code=current_language,
                    translations__slug=slug,
                    translations__published_revision__isnull=False,
                    translations__published_revision__status=(
                        UniversityTranslationRevision.Status.PUBLISHED
                    ),
                    translations__published_revision__translation_id=F(
                        "translations__pk"
                    ),
                )
                .distinct()
                .first()
            )

            if university is not None:
                return university, current_language

        return None, None
