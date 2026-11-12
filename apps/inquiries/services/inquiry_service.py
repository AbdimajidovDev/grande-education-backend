
from django.db import IntegrityError, transaction
from rest_framework.exceptions import APIException

from apps.inquiries.models import Inquiry, InquiryActivity


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
