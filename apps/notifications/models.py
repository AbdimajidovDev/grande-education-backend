import uuid

from django.conf import settings
from django.db import models


class Notification(models.Model):
    """CMS xodimiga yuborilgan bildirishnoma.

    PostgreSQL asosiy manba hisoblanadi: WebSocket faqat real-time
    yetkazish uchun ishlatiladi, offline xodim REST orqali oladi.
    """

    class Type(models.TextChoices):
        # Inquiries
        INQUIRY_CREATED = "inquiry_created", "Yangi ariza"
        INQUIRY_ASSIGNED = "inquiry_assigned", "Ariza biriktirildi"
        INQUIRY_UNASSIGNED = "inquiry_unassigned", "Ariza boshqa xodimga o'tkazildi"
        INQUIRY_STATUS_CHANGED = "inquiry_status_changed", "Ariza holati o'zgardi"
        INQUIRY_COMMENT_ADDED = "inquiry_comment_added", "Arizaga izoh qo'shildi"
        INQUIRY_UPDATED = "inquiry_updated", "Ariza ma'lumotlari o'zgardi"

        # Admissions
        ADMISSION_CREATED = "admission_created", "Yangi admission"
        ADMISSION_CURATOR_ASSIGNED = "admission_curator_assigned", "Kurator biriktirildi"
        ADMISSION_CURATOR_UNASSIGNED = (
            "admission_curator_unassigned",
            "Kuratorlik boshqa xodimga o'tkazildi",
        )
        ADMISSION_STAGE_CHANGED = "admission_stage_changed", "Admission bosqichi o'zgardi"
        ADMISSION_CANCELLED = "admission_cancelled", "Admission bekor qilindi"
        ADMISSION_RESTORED = "admission_restored", "Admission tiklandi"
        ADMISSION_COMMENT_ADDED = "admission_comment_added", "Admissionga izoh qo'shildi"

        # CMS moderation
        REVISION_SUBMITTED = "revision_submitted", "Revision ko'rib chiqishga yuborildi"
        REVISION_APPROVED = "revision_approved", "Revision tasdiqlandi"
        REVISION_REJECTED = "revision_rejected", "Revision rad etildi"
        REVISION_PUBLISHED = "revision_published", "Revision nashr qilindi"

    class EntityType(models.TextChoices):
        INQUIRY = "inquiry", "Inquiry"
        ADMISSION = "admission", "Admission"
        UNIVERSITY_REVISION = "university_revision", "University revision"
        UNIVERSITY_TRANSLATION_REVISION = (
            "university_translation_revision",
            "University translation revision",
        )
        FAQ_REVISION = "faq_revision", "FAQ revision"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        # Alohida FK index kerak emas: quyidagi composite indexlar
        # recipient_id bilan boshlanadi.
        db_index=False,
        verbose_name="Qabul qiluvchi",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="triggered_notifications",
        verbose_name="Amalni bajargan xodim",
    )

    type = models.CharField(max_length=50, choices=Type.choices)
    title = models.CharField(max_length=255)
    message = models.TextField(blank=True, default="")

    entity_type = models.CharField(max_length=50, choices=EntityType.choices)
    entity_id = models.CharField(max_length=64)
    data = models.JSONField(default=dict, blank=True)

    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications"
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ["-created_at"]
        indexes = [
            # Ro'yxat (is_read filtri bilan yoki filtrsiz) va unread count.
            models.Index(
                fields=["recipient", "is_read", "-created_at"],
                name="notif_recipient_read_idx",
            ),
            models.Index(
                fields=["recipient", "-created_at"],
                name="notif_recipient_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.recipient_id} - {self.type}"
