from django.db import models

# Create your models here.

import uuid

from django.conf import settings
from django.db import models


class InquiryCategory(models.Model):
    slug = models.SlugField(max_length=120, unique=True,)
    is_active = models.BooleanField(default=True,)
    created_at = models.DateTimeField(auto_now_add=True,)
    updated_at = models.DateTimeField(auto_now=True,)

    class Meta:
        verbose_name = "Inquiry category"
        verbose_name_plural = "Inquiry categories"
        ordering = ["slug"]

    def __str__(self):
        return self.slug



class InquiryCategoryTranslation(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    category = models.ForeignKey(
        InquiryCategory,
        on_delete=models.PROTECT,
        related_name="translations",
    )

    language_code = models.CharField(max_length=10)

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Inquiry category translation"
        verbose_name_plural = "Inquiry category translations"
        ordering = ["category", "language_code"]
        constraints = [
            models.UniqueConstraint(
                fields=["category", "language_code"],
                name="unique_inquiry_category_language",
            ),
        ]

    def __str__(self):
        return f"{self.category.slug} ({self.language_code})"



class Inquiry(models.Model):
    class ContactMethod(models.TextChoices):
        PHONE = "phone", "Telefon"
        TELEGRAM = "telegram", "Telegram"
        WHATSAPP = "whatsapp", "WhatsApp"

    class Status(models.TextChoices):
        NEW = "new", "Yangi"
        IN_PROGRESS = "in_progress", "Jarayonda"
        CONTACTED = "contacted", "Bog‘lanildi"
        COMPLETED = "completed", "Yakunlandi"
        CANCELLED = "cancelled", "Bekor qilindi"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, )

    category = models.ForeignKey(
        "inquiries.InquiryCategory",
        on_delete=models.PROTECT,
        related_name="inquiries",
    )

    university = models.ForeignKey(
        "universities.University",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inquiries",
    )

    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20)
    email = models.EmailField(blank=True)

    contact_method = models.CharField(max_length=20, choices=ContactMethod.choices,)

    message = models.TextField(blank=True)

    consent_accepted = models.BooleanField(default=False)
    consent_version = models.CharField(max_length=20)

    locale = models.CharField(max_length=10, default="uz",)

    idempotency_key = models.UUIDField(unique=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
    )

    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_inquiries",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Inquiry"
        verbose_name_plural = "Inquiries"
        ordering = ["-created_at"]
        permissions = [
            (
                "view_all_inquiries",
                "Can view all inquiries",
            ),
            (
                "change_inquiry_status",
                "Can change inquiry status",
            ),
            (
                "assign_inquiry",
                "Can assign inquiries to employees",
            ),
            (
                "view_inquiry_activity",
                "Can view inquiry activity",
            ),
        ]


    def __str__(self):
        return f"{self.full_name} - {self.phone_number}"



class InquiryActivity(models.Model):
    class Action(models.TextChoices):
        CREATED = "created", "Ariza yaratildi"
        STATUS_CHANGED = "status_changed", "Holat o‘zgartirildi"
        ASSIGNED = "assigned", "Xodim biriktirildi"
        COMMENT = "comment", "Izoh qo‘shildi"

    inquiry = models.ForeignKey("inquiries.Inquiry", on_delete=models.CASCADE, related_name="activities",)

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inquiry_activities",
    )

    action = models.CharField(max_length=20, choices=Action.choices, )
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Inquiry activity"
        verbose_name_plural = "Inquiry activities"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.inquiry.full_name} - {self.get_action_display()}"
