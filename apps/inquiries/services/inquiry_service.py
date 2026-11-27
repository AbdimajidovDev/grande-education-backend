
import uuid

from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from rest_framework.exceptions import APIException

from apps.inquiries.models import Inquiry, InquiryActivity
from apps.rbac.services.role_service import RoleService


class IdempotencyConflict(APIException):
    status_code = 409
    default_detail = (
        "This idempotency key has already been used "
        "with different inquiry data."
    )
    default_code = "idempotency_conflict"


def _is_same_request(inquiry, data):
    comparable_fields = (
        "category",
        "university",
        "full_name",
        "phone_number",
        "email",
        "contact_method",
        "message",
        "consent_accepted",
        "consent_version",
        "locale",
    )

    for field in comparable_fields:
        incoming_value = data.get(field)

        if field in ("category", "university"):
            incoming_value = (
                incoming_value.pk if incoming_value else None
            )
            existing_value = getattr(inquiry, f"{field}_id")
        else:
            existing_value = getattr(inquiry, field)

        if incoming_value != existing_value:
            return False

    return True


def create_inquiry(validated_data):
    data = validated_data.copy()
    data.setdefault("email", "")
    data.setdefault("message", "")
    data.setdefault("university", None)
    data.setdefault("locale", "uz")
    idempotency_key = data["idempotency_key"]

    try:
        with transaction.atomic():
            existing = Inquiry.objects.filter(
                idempotency_key=idempotency_key
            ).first()

            if existing:
                if not _is_same_request(existing, data):
                    raise IdempotencyConflict()

                return existing, False

            inquiry = Inquiry.objects.create(**data)

            InquiryActivity.objects.create(
                inquiry=inquiry,
                action=InquiryActivity.Action.CREATED,
                note="Ariza foydalanuvchi tomonidan yuborildi.",
            )

            return inquiry, True

    except IntegrityError:
        existing = Inquiry.objects.filter(
            idempotency_key=idempotency_key
        ).first()

        if existing:
            if not _is_same_request(existing, data):
                raise IdempotencyConflict()

            return existing, False

        raise


def _ensure_inquiry_permission(actor, permission: str) -> None:
    if actor is None or not actor.is_authenticated or not actor.is_active:
        raise PermissionDenied(
            "Bu amalni bajarish uchun faol foydalanuvchi bo'lishingiz kerak."
        )

    if actor.is_superuser:
        return

    permissions = RoleService._get_actor_role_permissions(actor)
    if permission not in permissions:
        raise PermissionDenied(
            "Ushbu amalni bajarish uchun ruxsatingiz mavjud emas."
        )


@transaction.atomic
def create_admin_inquiry(*, validated_data: dict, actor) -> Inquiry:
    """Admin/call-center xodimi tomonidan yangi lead (Inquiry) yaratadi."""

    _ensure_inquiry_permission(actor, "inquiries.add_inquiry")

    data = validated_data.copy()
    note = (data.pop("note", "") or "").strip()
    assignee = data.get("assignee")

    if assignee is not None and assignee.pk != actor.pk:
        _ensure_inquiry_permission(actor, "inquiries.assign_inquiry")

    data.setdefault("email", "")
    data.setdefault("message", "")
    data.setdefault("university", None)
    data.setdefault("contact_method", Inquiry.ContactMethod.PHONE)
    data.setdefault("locale", "uz")
    data["consent_accepted"] = True
    data["consent_version"] = "admin-manual"
    data["idempotency_key"] = data.get("idempotency_key") or uuid.uuid4()

    inquiry = Inquiry.objects.create(**data)

    activity_note = f"Lead admin ({actor.username}) tomonidan yaratildi."
    if note:
        activity_note = f"{activity_note} Izoh: {note}"

    InquiryActivity.objects.create(
        inquiry=inquiry,
        actor=actor,
        action=InquiryActivity.Action.CREATED,
        note=activity_note,
    )

    return inquiry



from django.db import transaction
from django.shortcuts import get_object_or_404


@transaction.atomic
def update_inquiry_status(
    *,
    inquiry_id,
    status: str,
    actor,
    note: str = "",
) -> Inquiry:
    inquiry = get_object_or_404(
        Inquiry.objects.select_for_update(),
        pk=inquiry_id,
    )

    if inquiry.status == status:
        return inquiry

    old_status = inquiry.status

    inquiry.status = status
    inquiry.save(update_fields=["status", "updated_at"])

    activity_note = (
        f"Status o'zgartirildi: {old_status} → {status}."
    )

    if note:
        activity_note = f"{activity_note} Izoh: {note}"

    InquiryActivity.objects.create(
        inquiry=inquiry,
        actor=actor,
        action=InquiryActivity.Action.STATUS_CHANGED,
        note=activity_note,
    )

    return inquiry



@transaction.atomic
def assign_inquiry(
    *,
    inquiry_id,
    assignee,
    actor,
    note: str = "",
) -> Inquiry:
    inquiry = get_object_or_404(
        Inquiry.objects.select_for_update(),
        pk=inquiry_id,
    )

    if inquiry.assignee_id == (assignee.pk if assignee else None):
        return inquiry

    previous_assignee = inquiry.assignee

    inquiry.assignee = assignee
    inquiry.save(update_fields=["assignee", "updated_at"])

    if assignee is None:
        action_note = "Ariza xodimdan yechildi."
    else:
        action_note = (
            f"Ariza {assignee.username} xodimiga biriktirildi."
        )

    if previous_assignee:
        action_note += (
            f" Oldingi mas'ul: {previous_assignee.username}."
        )

    if note:
        action_note += f" Izoh: {note}"

    InquiryActivity.objects.create(
        inquiry=inquiry,
        actor=actor,
        action=InquiryActivity.Action.ASSIGNED,
        note=action_note,
    )

    return inquiry



def add_inquiry_comment(
    *,
    inquiry_id,
    actor,
    note: str,
) -> InquiryActivity:
    inquiry = get_object_or_404(
        Inquiry,
        pk=inquiry_id,
    )

    return InquiryActivity.objects.create(
        inquiry=inquiry,
        actor=actor,
        action=InquiryActivity.Action.COMMENT,
        note=note,
    )


@transaction.atomic
def update_inquiry(
    *,
    inquiry_id,
    validated_data: dict,
    actor,
) -> Inquiry:
    """Ariza ma'lumotlarini tahrirlaydi va o'zgarishlarni faoliyat tarixiga yozadi."""

    _ensure_inquiry_permission(actor, "inquiries.change_inquiry")

    data = validated_data.copy()
    note = (data.pop("note", "") or "").strip()

    protected_fields = {
        "status",
        "assignee",
        "assignee_id",
        "consent_accepted",
        "consent_version",
        "idempotency_key",
    }
    if protected_fields.intersection(data):
        raise ValueError(
            "Status, assignee va tizim maydonlari bu funksiya orqali o'zgartirilmaydi."
        )

    inquiry = get_object_or_404(
        Inquiry.objects.select_for_update().select_related(
            "category",
            "university",
            "assignee",
        ),
        pk=inquiry_id,
    )

    changed_fields = []
    updated_fields = []

    for field, new_value in data.items():
        if getattr(inquiry, field) == new_value:
            continue

        setattr(inquiry, field, new_value)
        updated_fields.append(field)
        changed_fields.append(field)

    if updated_fields:
        inquiry.save(update_fields=[*updated_fields, "updated_at"])

        activity_note = (
            f"Ma'lumotlar tahrirlandi ({', '.join(changed_fields)})."
        )
        if note:
            activity_note = f"{activity_note} Izoh: {note}"

        InquiryActivity.objects.create(
            inquiry=inquiry,
            actor=actor,
            action=InquiryActivity.Action.DETAILS_UPDATED,
            note=activity_note,
        )

    return inquiry


@transaction.atomic
def delete_inquiry(
    *,
    inquiry_id,
    actor,
) -> None:
    """Arizani va uning kaskad faoliyat tarixini o'chiradi."""

    _ensure_inquiry_permission(actor, "inquiries.delete_inquiry")

    inquiry = get_object_or_404(
        Inquiry.objects.select_for_update(),
        pk=inquiry_id,
    )
    inquiry.delete()
