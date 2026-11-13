
import logging

from django.db import transaction

from apps.teachers.models import Teacher, TeacherTranslation
from apps.teachers.services.image_service import process_teacher_image

logger = logging.getLogger(__name__)


def _schedule_file_deletion(*, storage, file_name: str) -> None:
    """
    Database transaction muvaffaqiyatli tugagandan keyin
    eski media faylni o'chirishni rejalashtiradi.
    """
    if not file_name:
        return

    def delete_file():
        try:
            storage.delete(file_name)
        except Exception:
            logger.exception(
                "Failed to delete teacher media file: %s",
                file_name,
            )

    transaction.on_commit(delete_file)


@transaction.atomic
def create_teacher(*, validated_data: dict) -> Teacher:
    data = validated_data.copy()
    translations_data = data.pop("translations")

    if "photo" in data:
        data["photo"] = process_teacher_image(data["photo"])

    teacher = Teacher.objects.create(**data)

    translations = [
        TeacherTranslation(
            teacher=teacher,
            **translation_data,
        )
        for translation_data in translations_data
    ]

    TeacherTranslation.objects.bulk_create(translations)

    return teacher


@transaction.atomic
def update_teacher(
    *,
    teacher: Teacher,
    validated_data: dict,
) -> Teacher:
    data = validated_data.copy()
    translations_data = data.pop("translations", None)

    old_photo_name = (
        teacher.photo.name
        if teacher.photo
        else None
    )
    photo_storage = teacher.photo.storage

    if "photo" in data:
        data["photo"] = process_teacher_image(data["photo"])

    for field, value in data.items():
        setattr(teacher, field, value)

    if data:
        teacher.save()

    if translations_data is not None:
        for translation_data in translations_data:
            language_code = translation_data["language_code"]

            defaults = {
                key: value
                for key, value in translation_data.items()
                if key != "language_code"
            }

            TeacherTranslation.objects.update_or_create(
                teacher=teacher,
                language_code=language_code,
                defaults=defaults,
            )

        if not data:
            Teacher.save(teacher, update_fields=["updated_at"])

    new_photo_name = (
        teacher.photo.name
        if teacher.photo
        else None
    )

    if old_photo_name and old_photo_name != new_photo_name:
        _schedule_file_deletion(
            storage=photo_storage,
            file_name=old_photo_name,
        )

    return teacher


@transaction.atomic
def delete_teacher(*, teacher: Teacher) -> None:
    photo_name = teacher.photo.name if teacher.photo else None
    photo_storage = teacher.photo.storage

    teacher.delete()

    if photo_name:
        _schedule_file_deletion(
            storage=photo_storage,
            file_name=photo_name,
        )
