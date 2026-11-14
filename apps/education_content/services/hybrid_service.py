from django.db import transaction

from apps.education_content.models import (
    HybridTeacher,
    HybridTeacherTranslation,
    LearningComponent,
    LearningComponentTranslation,
)
from .file_service import (
    schedule_file_deletion,
    delete_file_if_unreferenced,
)



def _sync_translations(
    *,
    instance,
    translation_model,
    relation_field: str,
    translations: list[dict],
):
    for item in translations:
        translation_data = item.copy()
        language_code = translation_data.pop("language_code")

        translation_model.objects.update_or_create(
            **{
                relation_field: instance,
                "language_code": language_code,
            },
            defaults=translation_data,
        )



def create_hybrid_teacher(*, translations: list, **validated_data):
    teacher = HybridTeacher(**validated_data)

    try:
        with transaction.atomic():
            teacher.save()

            _sync_translations(
                instance=teacher,
                translation_model=HybridTeacherTranslation,
                relation_field="teacher",
                translations=translations,
            )


    except Exception:
        image = teacher.image

        if image and image.name and image._committed:
            delete_file_if_unreferenced(
                storage=image.storage,
                file_name=image.name,
            )

        raise

    return teacher




def update_hybrid_teacher(
    *,
    teacher: HybridTeacher,
    translations: list | None = None,
    **validated_data,
):
    old_image_name = (
        teacher.image.name if teacher.image else None
    )
    image_storage = teacher.image.storage

    has_new_image = (
        "image" in validated_data
        and validated_data["image"] is not None
    )

    try:
        with transaction.atomic():
            for field, value in validated_data.items():
                setattr(teacher, field, value)

            if validated_data:
                teacher.save(update_fields=[
                    *validated_data.keys(),
                    "updated_at",
                ])

            if translations is not None:
                _sync_translations(
                    instance=teacher,
                    translation_model=HybridTeacherTranslation,
                    relation_field="teacher",
                    translations=translations,
                )


    except Exception:
        image = teacher.image

        if (
                has_new_image
                and image
                and image.name
                and image._committed
                and image.name != old_image_name
        ):
            delete_file_if_unreferenced(
                storage=image_storage,
                file_name=image.name,
            )

        raise

    new_image_name = (
        teacher.image.name if teacher.image else None
    )

    if old_image_name and old_image_name != new_image_name:
        schedule_file_deletion(
            storage=image_storage,
            file_name=old_image_name,
        )

    return teacher



@transaction.atomic
def delete_hybrid_teacher(*, teacher: HybridTeacher):
    image_name = teacher.image.name if teacher.image else None
    image_storage = teacher.image.storage

    teacher.delete()

    if image_name:
        schedule_file_deletion(
            storage=image_storage,
            file_name=image_name,
        )


@transaction.atomic
def create_learning_component(*, translations: list, **validated_data):
    component = LearningComponent.objects.create(**validated_data)

    _sync_translations(
        instance=component,
        translation_model=LearningComponentTranslation,
        relation_field="component",
        translations=translations,
    )

    return component


@transaction.atomic
def update_learning_component(
    *,
    component: LearningComponent,
    translations: list | None = None,
    **validated_data,
):
    for field, value in validated_data.items():
        setattr(component, field, value)

    if validated_data:
        component.save(update_fields=[
            *validated_data.keys(),
            "updated_at",
        ])

    if translations is not None:
        _sync_translations(
            instance=component,
            translation_model=LearningComponentTranslation,
            relation_field="component",
            translations=translations,
        )

    return component


@transaction.atomic
def delete_learning_component(*, component: LearningComponent):
    component.delete()
