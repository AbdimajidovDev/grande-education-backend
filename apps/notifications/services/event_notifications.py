"""Biznes hodisalari uchun bildirishnoma dispatcherlari.

Har bir funksiya tegishli biznes service ichidan (tranzaksiya ichida)
aniq chaqiriladi — signal ishlatilmaydi. Bu yerda faqat "kimga" va
"qanday matn" hal qilinadi; yaratish va yetkazish NotificationService'da.

Xavfsizlik qoidalari:
* actor o'z harakati haqida xabar olmaydi (NotificationService);
* nofaol foydalanuvchiga yuborilmaydi;
* obyektni ko'rish huquqi (scope bilan) bo'lmagan xodimga obyekt
  tafsilotlari (PII) yuborilmaydi.
"""

from collections.abc import Iterable

from apps.notifications.models import Notification
from apps.notifications.selectors.recipient_selectors import (
    ADMISSION_VIEW_PERMISSIONS,
    FAQ_VIEW_PERMISSIONS,
    INQUIRY_VIEW_ALL_PERMISSION,
    INQUIRY_VIEW_PERMISSIONS,
    UNIVERSITY_TRANSLATION_VIEW_PERMISSIONS,
    UNIVERSITY_VIEW_PERMISSIONS,
    can_view_admission,
    can_view_inquiry,
    get_active_users_with_permissions,
    user_has_any_permission,
)
from apps.notifications.services.notification_service import NotificationService

Type = Notification.Type
EntityType = Notification.EntityType

MAX_NOTE_PREVIEW = 200

# Mas'ul xodim bilishi shart bo'lgan Inquiry maydonlari. Qolgan maydonlar
# (masalan, message matni yoki locale) o'zgarsa bildirishnoma yuborilmaydi.
INQUIRY_IMPORTANT_FIELDS = (
    "full_name",
    "phone_number",
    "email",
    "contact_method",
    "category",
    "university",
)


def _preview(text: str) -> str:
    text = (text or "").strip()
    if len(text) <= MAX_NOTE_PREVIEW:
        return text
    return f"{text[:MAX_NOTE_PREVIEW - 1]}…"


def _choice_label(choices_cls, value) -> str:
    try:
        return str(choices_cls(value).label)
    except ValueError:
        return str(value or "")


# ============================================================================
# Inquiries
# ============================================================================

def _notify_inquiry_assignee(
    *,
    inquiry,
    actor,
    type: str,
    title: str,
    message: str,
    data: dict | None = None,
) -> None:
    assignee = inquiry.assignee
    if assignee is None:
        return

    if not can_view_inquiry(assignee, assignee_id=inquiry.assignee_id):
        return

    NotificationService.notify(
        recipient=assignee,
        actor=actor,
        type=type,
        title=title,
        message=message,
        entity_type=EntityType.INQUIRY,
        entity_id=inquiry.pk,
        data=data,
    )


def notify_public_inquiry_created(*, inquiry) -> None:
    """Saytdan yangi ariza: barcha arizalarni ko'ra oladigan xodimlarga."""

    recipients = get_active_users_with_permissions(
        required=INQUIRY_VIEW_ALL_PERMISSION,
    )

    NotificationService.notify_many(
        recipients=recipients,
        type=Type.INQUIRY_CREATED,
        title="Saytdan yangi ariza",
        message=f"{inquiry.full_name} saytdan yangi ariza yubordi.",
        entity_type=EntityType.INQUIRY,
        entity_id=inquiry.pk,
        data={
            "status": inquiry.status,
            "category": inquiry.category.slug,
            "contact_method": inquiry.contact_method,
        },
    )


def notify_inquiry_assigned(
    *,
    inquiry,
    actor,
    previous_assignee=None,
) -> None:
    """Yangi mas'ulga biriktirish, eski mas'ulga esa olib qo'yilganini bildiradi."""

    _notify_inquiry_assignee(
        inquiry=inquiry,
        actor=actor,
        type=Type.INQUIRY_ASSIGNED,
        title="Sizga ariza biriktirildi",
        message=f"{inquiry.full_name} arizasi sizga biriktirildi.",
        data={"status": inquiry.status},
    )

    if previous_assignee is None or previous_assignee.pk == inquiry.assignee_id:
        return

    # Eski mas'ul endi arizani ko'ra olmasligi mumkin — bunday holda
    # mijozning shaxsiy ma'lumotlari xabarga qo'shilmaydi.
    if can_view_inquiry(previous_assignee, assignee_id=inquiry.assignee_id):
        message = f"{inquiry.full_name} arizasi boshqa xodimga o'tkazildi."
    elif user_has_any_permission(previous_assignee, INQUIRY_VIEW_PERMISSIONS):
        message = "Sizga biriktirilgan ariza boshqa xodimga o'tkazildi."
    else:
        return

    NotificationService.notify(
        recipient=previous_assignee,
        actor=actor,
        type=Type.INQUIRY_UNASSIGNED,
        title="Ariza sizdan olindi",
        message=message,
        entity_type=EntityType.INQUIRY,
        entity_id=inquiry.pk,
    )


def notify_inquiry_status_changed(
    *,
    inquiry,
    actor,
    old_status: str,
) -> None:
    status_cls = type(inquiry).Status
    old_label = _choice_label(status_cls, old_status)
    new_label = _choice_label(status_cls, inquiry.status)

    _notify_inquiry_assignee(
        inquiry=inquiry,
        actor=actor,
        type=Type.INQUIRY_STATUS_CHANGED,
        title="Ariza holati o'zgardi",
        message=f"{inquiry.full_name} arizasi: {old_label} → {new_label}.",
        data={"old_status": old_status, "new_status": inquiry.status},
    )


def notify_inquiry_comment_added(*, inquiry, actor, note: str) -> None:
    _notify_inquiry_assignee(
        inquiry=inquiry,
        actor=actor,
        type=Type.INQUIRY_COMMENT_ADDED,
        title="Arizaga yangi izoh",
        message=f"{inquiry.full_name} arizasiga izoh: {_preview(note)}",
    )


def notify_inquiry_updated(
    *,
    inquiry,
    actor,
    changed_fields: Iterable[str],
) -> None:
    """Faqat muhim maydonlar o'zgarganda mas'ul xodimni xabardor qiladi."""

    important = [
        field for field in changed_fields
        if field in INQUIRY_IMPORTANT_FIELDS
    ]
    if not important:
        return

    _notify_inquiry_assignee(
        inquiry=inquiry,
        actor=actor,
        type=Type.INQUIRY_UPDATED,
        title="Ariza ma'lumotlari o'zgardi",
        message=f"{inquiry.full_name} arizasida o'zgarish: {', '.join(important)}.",
        data={"changed_fields": important},
    )


# ============================================================================
# Admissions
# ============================================================================

def _notify_admission_user(
    *,
    admission,
    recipient,
    actor,
    type: str,
    title: str,
    message: str,
    data: dict | None = None,
) -> None:
    if recipient is None:
        return

    if not can_view_admission(recipient, curator_id=admission.curator_id):
        return

    NotificationService.notify(
        recipient=recipient,
        actor=actor,
        type=type,
        title=title,
        message=message,
        entity_type=EntityType.ADMISSION,
        entity_id=admission.pk,
        data=data,
    )


def notify_admission_created(*, admission, actor) -> None:
    """Kuratorga va (admissionni ko'ra olsa) tegishli inquiry mas'uliga."""

    curator = admission.curator
    stage_label = admission.get_stage_display()

    _notify_admission_user(
        admission=admission,
        recipient=curator,
        actor=actor,
        type=Type.ADMISSION_CREATED,
        title="Yangi admission biriktirildi",
        message=f"{admission.full_name} uchun admission ochildi ({stage_label}).",
        data={"stage": admission.stage},
    )

    inquiry = admission.inquiry
    inquiry_assignee = inquiry.assignee if inquiry is not None else None

    if inquiry_assignee is None or inquiry_assignee.pk == admission.curator_id:
        return

    _notify_admission_user(
        admission=admission,
        recipient=inquiry_assignee,
        actor=actor,
        type=Type.ADMISSION_CREATED,
        title="Arizangiz bo'yicha admission ochildi",
        message=f"{admission.full_name} arizasi bo'yicha admission ochildi ({stage_label}).",
        data={"stage": admission.stage, "inquiry_id": str(inquiry.pk)},
    )


def notify_admission_curator_changed(
    *,
    admission,
    actor,
    previous_curator=None,
) -> None:
    _notify_admission_user(
        admission=admission,
        recipient=admission.curator,
        actor=actor,
        type=Type.ADMISSION_CURATOR_ASSIGNED,
        title="Siz kurator etib biriktirildingiz",
        message=f"{admission.full_name} admissioni sizga biriktirildi.",
        data={"stage": admission.stage},
    )

    if previous_curator is None or previous_curator.pk == admission.curator_id:
        return

    if can_view_admission(previous_curator, curator_id=admission.curator_id):
        message = f"{admission.full_name} admissioni boshqa kuratorga o'tkazildi."
    elif user_has_any_permission(previous_curator, ADMISSION_VIEW_PERMISSIONS):
        message = "Sizga biriktirilgan admission boshqa kuratorga o'tkazildi."
    else:
        return

    NotificationService.notify(
        recipient=previous_curator,
        actor=actor,
        type=Type.ADMISSION_CURATOR_UNASSIGNED,
        title="Admission sizdan olindi",
        message=message,
        entity_type=EntityType.ADMISSION,
        entity_id=admission.pk,
    )


def notify_admission_stage_changed(
    *,
    admission,
    actor,
    old_stage: str,
) -> None:
    stage_cls = type(admission).Stage
    new_stage = admission.stage
    old_label = _choice_label(stage_cls, old_stage)
    new_label = _choice_label(stage_cls, new_stage)

    if new_stage == stage_cls.CANCELLED:
        notification_type = Type.ADMISSION_CANCELLED
        title = "Admission bekor qilindi"
        message = f"{admission.full_name} admissioni bekor qilindi."
    else:
        notification_type = Type.ADMISSION_STAGE_CHANGED
        title = "Admission bosqichi o'zgardi"
        message = f"{admission.full_name}: {old_label} → {new_label}."

    _notify_admission_user(
        admission=admission,
        recipient=admission.curator,
        actor=actor,
        type=notification_type,
        title=title,
        message=message,
        data={"old_stage": old_stage, "new_stage": new_stage},
    )


def notify_admission_restored(*, admission, actor) -> None:
    _notify_admission_user(
        admission=admission,
        recipient=admission.curator,
        actor=actor,
        type=Type.ADMISSION_RESTORED,
        title="Admission qayta tiklandi",
        message=(
            f"{admission.full_name} admissioni "
            f"{admission.get_stage_display()} bosqichiga tiklandi."
        ),
        data={"stage": admission.stage},
    )


def notify_admission_comment_added(*, admission, actor, note: str) -> None:
    _notify_admission_user(
        admission=admission,
        recipient=admission.curator,
        actor=actor,
        type=Type.ADMISSION_COMMENT_ADDED,
        title="Admissionga yangi izoh",
        message=f"{admission.full_name} admissioniga izoh: {_preview(note)}",
    )


# ============================================================================
# CMS moderation (University / University translation / FAQ revisions)
# ============================================================================

REVISION_UNIVERSITY = "university"
REVISION_UNIVERSITY_TRANSLATION = "university_translation"
REVISION_FAQ = "faq"


def _revision_context(kind: str, revision) -> dict:
    if kind == REVISION_UNIVERSITY:
        return {
            "entity_type": EntityType.UNIVERSITY_REVISION,
            "approve_permission": "universities.approve_university",
            "view_permissions": UNIVERSITY_VIEW_PERMISSIONS,
            "subject": f"Universitet revisioni #{revision.revision_number}",
            "data": {
                "university_id": str(revision.university_id),
                "revision_number": revision.revision_number,
            },
        }

    translation = revision.translation

    if kind == REVISION_UNIVERSITY_TRANSLATION:
        return {
            "entity_type": EntityType.UNIVERSITY_TRANSLATION_REVISION,
            "approve_permission": "universities.approve_university",
            "view_permissions": UNIVERSITY_TRANSLATION_VIEW_PERMISSIONS,
            "subject": (
                f"Universitet tarjimasi ({translation.language_code}) "
                f"revisioni #{revision.revision_number}"
            ),
            "data": {
                "university_id": str(translation.university_id),
                "translation_id": str(translation.pk),
                "language_code": translation.language_code,
                "revision_number": revision.revision_number,
            },
        }

    if kind == REVISION_FAQ:
        return {
            "entity_type": EntityType.FAQ_REVISION,
            "approve_permission": "universities.approve_faq",
            "view_permissions": FAQ_VIEW_PERMISSIONS,
            "subject": (
                f"FAQ tarjimasi ({translation.language_code}) "
                f"revisioni #{revision.revision_number}"
            ),
            "data": {
                "faq_id": str(translation.faq_id),
                "translation_id": str(translation.pk),
                "language_code": translation.language_code,
                "revision_number": revision.revision_number,
            },
        }

    raise ValueError(f"Noma'lum revision turi: {kind}")


def notify_revision_submitted(*, kind: str, revision, actor) -> None:
    """Review'ga yuborildi: tasdiqlash va ko'rish huquqi bor xodimlarga."""

    context = _revision_context(kind, revision)
    recipients = get_active_users_with_permissions(
        required=context["approve_permission"],
        any_of=context["view_permissions"],
    )

    NotificationService.notify_many(
        recipients=recipients,
        actor=actor,
        type=Type.REVISION_SUBMITTED,
        title="Revision ko'rib chiqishga yuborildi",
        message=f"{context['subject']} tasdiqlashingizni kutmoqda.",
        entity_type=context["entity_type"],
        entity_id=revision.pk,
        data=context["data"],
    )


def _notify_revision_author(
    *,
    kind: str,
    revision,
    actor,
    type: str,
    title: str,
    message_suffix: str,
    extra_data: dict | None = None,
) -> None:
    context = _revision_context(kind, revision)
    author = revision.created_by

    if not user_has_any_permission(author, context["view_permissions"]):
        return

    NotificationService.notify(
        recipient=author,
        actor=actor,
        type=type,
        title=title,
        message=f"{context['subject']} {message_suffix}",
        entity_type=context["entity_type"],
        entity_id=revision.pk,
        data={**context["data"], **(extra_data or {})},
    )


def notify_revision_approved(*, kind: str, revision, actor) -> None:
    _notify_revision_author(
        kind=kind,
        revision=revision,
        actor=actor,
        type=Type.REVISION_APPROVED,
        title="Revision tasdiqlandi",
        message_suffix="tasdiqlandi.",
    )


def notify_revision_rejected(*, kind: str, revision, actor, reason: str) -> None:
    _notify_revision_author(
        kind=kind,
        revision=revision,
        actor=actor,
        type=Type.REVISION_REJECTED,
        title="Revision rad etildi",
        message_suffix=f"rad etildi. Sabab: {_preview(reason)}",
        extra_data={"reason": reason},
    )


def notify_revision_published(*, kind: str, revision, actor) -> None:
    _notify_revision_author(
        kind=kind,
        revision=revision,
        actor=actor,
        type=Type.REVISION_PUBLISHED,
        title="Revision nashr qilindi",
        message_suffix="nashr qilindi.",
    )
