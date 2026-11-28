
from django.core.exceptions import PermissionDenied
from django.db import transaction

from apps.admissions.models import Admission, AdmissionActivity
from apps.notifications.services import event_notifications
from django.db import models

@transaction.atomic
def create_admission(
    *,
    validated_data: dict,
    actor=None,
) -> Admission:
    """
    Yangi Admission yaratadi va faoliyat tarixiga yozadi.
    """

    admission = Admission.objects.create(**validated_data)

    AdmissionActivity.objects.create(
        admission=admission,
        actor=actor,
        action=AdmissionActivity.Action.CREATED,
        new_value=admission.stage,
    )

    event_notifications.notify_admission_created(admission=admission, actor=actor)

    return admission


@transaction.atomic
def update_admission(
    *,
    admission_id,
    validated_data: dict,
    actor=None,
) -> Admission:
    """
    Admission ma'lumotlarini yangilaydi
    va har bir o'zgarishni audit tarixiga yozadi.
    """

    protected_fields = {"stage", "curator", "curator_id"}

    if protected_fields.intersection(validated_data):
        raise ValueError(
            "Stage va curator alohida service orqali yangilanishi kerak."
        )

    admission = Admission.objects.select_for_update().get(
        pk=admission_id,
    )

    activities = []
    updated_fields = []

    for field, new_value in validated_data.items():
        old_value = getattr(admission, field)

        if old_value == new_value:
            continue

        old_value_display = (
            str(old_value.pk)
            if isinstance(old_value, models.Model)
            else str(old_value or "")
        )

        new_value_display = (
            str(new_value.pk)
            if isinstance(new_value, models.Model)
            else str(new_value or "")
        )

        activities.append(
            AdmissionActivity(
                admission=admission,
                actor=actor,
                action=AdmissionActivity.Action.DETAILS_UPDATED,
                field_name=field,
                old_value=old_value_display,
                new_value=new_value_display,
            )
        )

        setattr(admission, field, new_value)
        updated_fields.append(field)

    if updated_fields:
        admission.save(
            update_fields=[*updated_fields, "updated_at"],
        )

        AdmissionActivity.objects.bulk_create(activities)

    return admission



# Qabul jarayonining standart ketma-ketligi (Admission.Stage tartibi).
STAGE_PIPELINE = (
    Admission.Stage.CONSULTATION,
    Admission.Stage.SELECTION,
    Admission.Stage.EXAMS,
    Admission.Stage.DOCUMENTS,
    Admission.Stage.ARRIVAL,
)


def validate_stage_transition(
    *,
    current_stage: str,
    new_stage: str,
    can_override: bool = False,
    note: str = "",
) -> None:
    """Admission bosqichi o'tishini tekshiradi.

    * O'sha bosqichga "o'tish" — no-op (xato emas).
    * Standart o'tish — keyingi bosqichga bitta qadam.
    * Har qanday faol bosqichdan CANCELLED ga o'tish (cancel_admission) ruxsat.
    * CANCELLED dan chiqish faqat restore_admission orqali.
    * Nostandart o'tish (bosqich tashlab o'tish yoki orqaga qaytish) faqat
      ``admissions.override_admission_stage_transition`` huquqi bilan
      (``can_override=True``) va sabab (note) ko'rsatilganda.

    OCHIQ BIZNES QARORI — ARRIVAL → CANCELLED:
        Hozir ARRIVAL (yakuniy) bosqichdan ham CANCELLED ga o'tishga ruxsat
        bor, chunki mavjud ``cancel_admission`` hech qanday bosqich cheklovini
        qo'ymagan. Bu biznes tomonidan tasdiqlanmagan; o'zgartirish faqat
        biznes qarori bilan (masalan, ARRIVAL'dan bekor qilishni taqiqlash
        yoki override talab qilish) va tegishli test bilan amalga oshirilsin.
        Batafsil: docs/admission-stage-rules.md.
    """

    if new_stage not in Admission.Stage.values:
        raise ValueError("Noto'g'ri Admission bosqichi.")

    if current_stage == new_stage:
        return

    if current_stage == Admission.Stage.CANCELLED:
        raise ValueError(
            "Bekor qilingan Admission faqat tiklash (restore) orqali qayta faollashtiriladi."
        )

    if current_stage not in STAGE_PIPELINE:
        raise ValueError("Admissionning joriy bosqichi noto'g'ri.")

    if new_stage == Admission.Stage.CANCELLED:
        return

    current_index = STAGE_PIPELINE.index(current_stage)
    new_index = STAGE_PIPELINE.index(new_stage)

    if new_index == current_index + 1:
        return

    if not can_override:
        raise PermissionDenied(
            "Bosqichlarni tashlab o'tish yoki orqaga qaytarish uchun "
            "maxsus ruxsat talab qilinadi."
        )

    if not (note or "").strip():
        raise ValueError(
            "Nostandart bosqich o'tishi uchun sabab (izoh) ko'rsatilishi shart."
        )


@transaction.atomic
def update_admission_stage(
    *,
    admission_id,
    stage: str,
    actor=None,
    note: str = "",
    can_override: bool = False,
) -> Admission:
    """
    Admission bosqichini o'zgartiradi.
    Nostandart o'tishlar maxsus permission bilan amalga oshiriladi.
    """

    admission = Admission.objects.select_for_update().get(
        pk=admission_id,
    )

    old_stage = admission.stage

    validate_stage_transition(
        current_stage=old_stage,
        new_stage=stage,
        can_override=can_override,
        note=note,
    )

    if old_stage == stage:
        return admission

    admission.stage = stage
    admission.save(
        update_fields=["stage", "updated_at"],
    )

    AdmissionActivity.objects.create(
        admission=admission,
        actor=actor,
        action=AdmissionActivity.Action.STAGE_CHANGED,
        old_value=old_stage,
        new_value=stage,
        note=note.strip(),
    )

    event_notifications.notify_admission_stage_changed(
        admission=admission,
        actor=actor,
        old_stage=old_stage,
    )

    return admission



@transaction.atomic
def assign_admission_curator(
    *,
    admission_id,
    curator,
    actor=None,
    note: str = "",
) -> Admission:
    """
    Admission uchun kurator biriktiradi va tarixga yozadi.
    """

    admission = Admission.objects.select_for_update().get(
        pk=admission_id,
    )

    old_curator_id = (
        str(admission.curator_id)
        if admission.curator_id
        else ""
    )

    new_curator_id = (
        str(curator.pk)
        if curator
        else ""
    )

    if old_curator_id == new_curator_id:
        return admission

    previous_curator = admission.curator
    admission.curator = curator
    admission.save(update_fields=["curator", "updated_at"])

    AdmissionActivity.objects.create(
        admission=admission,
        actor=actor,
        action=AdmissionActivity.Action.CURATOR_ASSIGNED,
        old_value=old_curator_id,
        new_value=new_curator_id,
        note=note,
    )

    event_notifications.notify_admission_curator_changed(
        admission=admission,
        actor=actor,
        previous_curator=previous_curator,
    )

    return admission


@transaction.atomic
def cancel_admission(
    *,
    admission_id,
    actor=None,
    note: str = "",
) -> Admission:
    """
    Admission jarayonini bekor qiladi.
    """

    return update_admission_stage(
        admission_id=admission_id,
        stage=Admission.Stage.CANCELLED,
        actor=actor,
        note=note,
    )


@transaction.atomic
def add_admission_comment(
    *,
    admission_id,
    actor,
    note: str,
) -> AdmissionActivity:
    """
    Admissionga izoh qo'shadi.
    """

    if not note or not note.strip():
        raise ValueError("Izoh bo'sh bo'lishi mumkin emas.")

    admission = Admission.objects.select_for_update().get(
        pk=admission_id,
    )

    activity = AdmissionActivity.objects.create(
        admission=admission,
        actor=actor,
        action=AdmissionActivity.Action.COMMENT,
        note=note.strip(),
    )

    event_notifications.notify_admission_comment_added(
        admission=admission,
        actor=actor,
        note=note,
    )

    return activity



@transaction.atomic
def restore_admission(
    *,
    admission_id,
    actor=None,
    note: str = "",
) -> Admission:
    """
    Bekor qilingan Admissionni bekor qilishdan oldingi
    bosqichiga qaytaradi.
    """

    admission = Admission.objects.select_for_update().get(
        pk=admission_id,
    )

    if admission.stage != Admission.Stage.CANCELLED:
        raise ValueError(
            "Faqat CANCELLED holatidagi Admission tiklanishi mumkin."
        )

    cancellation = (
        AdmissionActivity.objects.filter(
            admission=admission,
            action=AdmissionActivity.Action.STAGE_CHANGED,
            new_value=Admission.Stage.CANCELLED,
        )
        .order_by("-created_at")
        .first()
    )

    if cancellation is None:
        raise ValueError(
            "Admissionning bekor qilinish tarixi topilmadi."
        )

    previous_stage = cancellation.old_value

    if previous_stage not in Admission.Stage.values:
        raise ValueError(
            "Admissionning avvalgi bosqichi noto'g'ri."
        )

    if previous_stage == Admission.Stage.CANCELLED:
        raise ValueError(
            "Admission avvalgi bosqichini tiklab bo'lmadi."
        )

    admission.stage = previous_stage
    admission.save(update_fields=["stage", "updated_at"])

    AdmissionActivity.objects.create(
        admission=admission,
        actor=actor,
        action=AdmissionActivity.Action.STAGE_CHANGED,
        old_value=Admission.Stage.CANCELLED,
        new_value=previous_stage,
        note=note or "Admission qayta faollashtirildi.",
    )

    event_notifications.notify_admission_restored(admission=admission, actor=actor)

    return admission

