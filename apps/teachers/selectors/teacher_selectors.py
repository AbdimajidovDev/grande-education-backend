
from django.db.models import Exists, OuterRef, Prefetch

from apps.teachers.models import Teacher, TeacherTranslation


def get_public_teachers(*, language_code: str):
    """
    Returns active teachers with requested language translations.
    Falls back to Uzbek when translation is unavailable.
    """

    languages = (
        [language_code]
        if language_code == "uz"
        else [language_code, "uz"]
    )

    available_translation = TeacherTranslation.objects.filter(
        teacher_id=OuterRef("pk"),
        language_code__in=languages,
    )

    translations_queryset = (
        TeacherTranslation.objects
        .filter(language_code__in=languages)
        .only(
            "id",
            "teacher_id",
            "language_code",
            "role",
            "experience",
            "bio",
            "skills",
        )
    )

    return (
        Teacher.objects
        .filter(is_active=True)
        .annotate(
            has_translation=Exists(available_translation),
        )
        .filter(has_translation=True)
        .prefetch_related(
            Prefetch(
                "translations",
                queryset=translations_queryset,
                to_attr="available_translations",
            )
        )
        .order_by("order", "full_name")
    )


def get_admin_teachers():
    """
    Returns all teachers for admin management.
    """

    return (
        Teacher.objects
        .prefetch_related("translations")
        .order_by("order", "full_name")
    )


def get_teacher_by_id(*, teacher_id):
    """
    Returns a single teacher by UUID.
    """

    return (
        Teacher.objects
        .prefetch_related("translations")
        .filter(pk=teacher_id)
        .first()
    )


def resolve_teacher_translation(teacher, language_code: str):
    """
    Returns requested language translation.
    Falls back to Uzbek.
    """

    translations = {
        translation.language_code: translation
        for translation in teacher.available_translations
    }

    return (
        translations.get(language_code)
        or translations.get("uz")
    )

