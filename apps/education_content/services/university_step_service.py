
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.education_content.models import (
    UniversityStep,
    UniversityStepPage,
    UniversityStepPageTranslation,
    UniversityStepTranslation,
)
from .file_service import (
    schedule_file_deletion,
    delete_file_if_unreferenced,
)

ACTIVE_STEPS_REQUIRED = 5


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


def _lock_page(page_id):
    return UniversityStepPage.objects.select_for_update().get(
        pk=page_id
    )


def _validate_active_steps_count(page):
    active_steps_count = UniversityStep.objects.filter(
        page=page,
        is_active=True,
    ).count()

    if active_steps_count != ACTIVE_STEPS_REQUIRED:
        raise ValidationError({
            "is_active": (
                f"Page must have exactly {ACTIVE_STEPS_REQUIRED} "
                f"active steps. Currently: {active_steps_count}."
            )
        })


# =========================================================
# University Step Page
# =========================================================

@transaction.atomic
def create_university_step_page(
    *,
    translations: list[dict],
    **validated_data,
):
    if validated_data.get("is_active", False):
        raise ValidationError({
            "is_active": (
                "Create the page as inactive first. "
                "Add all five steps before activating it."
            )
        })

    page = UniversityStepPage.objects.create(**validated_data)

    _sync_translations(
        instance=page,
        translation_model=UniversityStepPageTranslation,
        relation_field="page",
        translations=translations,
    )

    return page


@transaction.atomic
def update_university_step_page(
    *,
    page: UniversityStepPage,
    translations: list[dict] | None = None,
    **validated_data,
):
    page = _lock_page(page.pk)

    activating = (
        validated_data.get("is_active", page.is_active)
        and not page.is_active
    )

    if activating:
        _validate_active_steps_count(page)

    for field, value in validated_data.items():
        setattr(page, field, value)

    if validated_data:
        page.save(
            update_fields=[
                *validated_data.keys(),
                "updated_at",
            ]
        )

    if translations is not None:
        _sync_translations(
            instance=page,
            translation_model=UniversityStepPageTranslation,
            relation_field="page",
            translations=translations,
        )

    return page



@transaction.atomic
def delete_university_step_page(*, page: UniversityStepPage):
    page = _lock_page(page.pk)

    # Sahifaga tegishli rasmlarni oldindan yig'amiz.
    steps = UniversityStep.objects.filter(
        page=page,
    ).only("id", "image")

    images_to_delete = [
        (step.image.storage, step.image.name)
        for step in steps
        if step.image
    ]

    # Sahifa va unga tegishli qadamlar DB'dan o'chiriladi.
    page.delete()

    # Faqat DB transaction muvaffaqiyatli yakunlangandan
    # keyin rasmlarni storage'dan o'chiramiz.
    for storage, file_name in images_to_delete:
        schedule_file_deletion(
            storage=storage,
            file_name=file_name,
        )


# =========================================================
# University Steps
# =========================================================


def create_university_step(
    *,
    translations: list[dict],
    **validated_data,
):
    step = UniversityStep(**validated_data)

    try:
        with transaction.atomic():
            page = _lock_page(validated_data["page"].pk)

            if page.is_active:
                raise ValidationError({
                    "page": (
                        "Cannot add steps to an active page. "
                        "Deactivate the page first."
                    )
                })

            step.page = page
            step.save()

            _sync_translations(
                instance=step,
                translation_model=UniversityStepTranslation,
                relation_field="step",
                translations=translations,
            )


    except Exception:
        image = step.image

        if image and image.name and image._committed:
            delete_file_if_unreferenced(
                storage=image.storage,
                file_name=image.name,
            )

        raise

    return step





def update_university_step(
    *,
    step: UniversityStep,
    translations: list[dict] | None = None,
    **validated_data,
):
    old_image_name = None
    image_storage = None
    new_image_name = None

    try:
        with transaction.atomic():
            page = _lock_page(step.page_id)

            step = UniversityStep.objects.select_for_update().get(
                pk=step.pk
            )

            if (
                "page" in validated_data
                and validated_data["page"].pk != step.page_id
            ):
                raise ValidationError({
                    "page": (
                        "Moving a step to another page "
                        "is not allowed."
                    )
                })

            structural_fields = (
                "step_number",
                "order",
                "is_active",
            )

            if page.is_active:
                structural_changes = [
                    field
                    for field in structural_fields
                    if field in validated_data
                    and getattr(step, field) != validated_data[field]
                ]

                if structural_changes:
                    raise ValidationError({
                        field: (
                            "Deactivate the page before changing "
                            "the step structure."
                        )
                        for field in structural_changes
                    })

            validated_data.pop("page", None)

            # Eski rasmni saqlab qolamiz.
            old_image_name = (
                step.image.name if step.image else None
            )
            image_storage = step.image.storage

            for field, value in validated_data.items():
                setattr(step, field, value)

            if validated_data:
                step.save(
                    update_fields=[
                        *validated_data.keys(),
                        "updated_at",
                    ]
                )

            if translations is not None:
                _sync_translations(
                    instance=step,
                    translation_model=UniversityStepTranslation,
                    relation_field="step",
                    translations=translations,
                )

            new_image_name = (
                step.image.name if step.image else None
            )



    except Exception:
        image = step.image

        if (
                image
                and image.name
                and image._committed
                and image.name != old_image_name
                and image_storage
        ):
            delete_file_if_unreferenced(
                storage=image_storage,
                file_name=image.name,
            )

        raise

    if old_image_name and old_image_name != new_image_name:
        schedule_file_deletion(
            storage=image_storage,
            file_name=old_image_name,
        )

    return step




@transaction.atomic
def delete_university_step(*, step: UniversityStep):
    page = _lock_page(step.page_id)

    if page.is_active:
        raise ValidationError({
            "detail": (
                "Cannot delete a step from an active page. "
                "Deactivate the page first."
            )
        })

    step = UniversityStep.objects.select_for_update().get(
        pk=step.pk
    )

    image_name = step.image.name if step.image else None
    image_storage = step.image.storage

    step.delete()

    if image_name:
        schedule_file_deletion(
            storage=image_storage,
            file_name=image_name,
        )
