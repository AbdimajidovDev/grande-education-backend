
import uuid

from django.conf import settings
from django.db import models
from django.db.models import F, Q


class University(models.Model):
    """Universitetning doimiy identifikatori va global nashr holatini saqlaydi."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Qoralama"
        REVIEW = "review", "Ko‘rib chiqilmoqda"
        PUBLISHED = "published", "Nashr qilingan"
        ARCHIVED = "archived", "Arxivlangan"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False,)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
        verbose_name="Umumiy holati",
    )

    published_revision = models.ForeignKey(
        "universities.UniversityRevision",
        on_delete=models.PROTECT,
        related_name="published_for_universities",
        null=True,
        blank=True,
        verbose_name="Joriy nashr qilingan versiya",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_universities",
        verbose_name="Yaratgan xodim",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="updated_universities",
        null=True,
        blank=True,
        verbose_name="Oxirgi tahrirlagan xodim",
    )
    rejection_reason = models.TextField(
        blank=True,
        default="",
        verbose_name="Rad etish sababi",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Universitet"
        verbose_name_plural = "Universitetlar"
        ordering = ["-created_at"]
        permissions = [
            (
                "submit_review_university",
                "Universitetni ko‘rib chiqishga yuborish",
            ),
            (
                "approve_university",
                "Universitetni tasdiqlash",
            ),
            (
                "reject_university",
                "Universitetni rad etish",
            ),
            (
                "publish_university",
                "Universitetni nashr qilish",
            ),
        ]
        indexes = [
            models.Index(
                fields=["status", "created_at"],
                name="univ_status_created_idx",
            ),
        ]

    def __str__(self):
        return str(self.pk)


class UniversityRevision(models.Model):
    """Universitetning umumiy ma’lumotlari va ularning versiyalarini saqlaydi."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Qoralama"
        REVIEW = "review", "Ko‘rib chiqilmoqda"
        PUBLISHED = "published", "Nashr qilingan"
        ARCHIVED = "archived", "Arxivlangan"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    university = models.ForeignKey(
        University,
        on_delete=models.PROTECT,
        related_name="revisions",
        verbose_name="Universitet",
    )

    revision_number = models.PositiveIntegerField(
        verbose_name="Versiya raqami",
    )

    city = models.CharField(
        max_length=150,
        verbose_name="Shahar",
    )
    country = models.CharField(
        max_length=150,
        verbose_name="Mamlakat",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
        verbose_name="Versiya holati",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_university_content_revisions",
        verbose_name="Yaratgan xodim",
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="approved_university_content_revisions",
        null=True,
        blank=True,
        verbose_name="Tasdiqlagan xodim",
    )

    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Tasdiqlangan vaqt",
    )
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Nashr qilingan vaqt",
    )
    scheduled_publish_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Rejalashtirilgan nashr vaqti",
    )
    rejection_reason = models.TextField(
        blank=True,
        verbose_name="Rad etish sababi",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Universitet versiyasi"
        verbose_name_plural = "Universitet versiyalari"
        ordering = ["-revision_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["university", "revision_number"],
                name="unique_university_revision_number",
            ),
        ]
        indexes = [
            models.Index(
                fields=["university", "status"],
                name="univ_content_revision_idx",
            ),
        ]

    def __str__(self):
        return f"{self.university_id} / revision {self.revision_number}"


class UniversityTranslation(models.Model):
    """Universitetning muayyan til uchun tarjimasini va joriy nashrini bog‘laydi."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    university = models.ForeignKey(
        University,
        on_delete=models.PROTECT,
        related_name="translations",
        verbose_name="Universitet",
    )

    language_code = models.CharField(
        max_length=10,
        verbose_name="Til kodi",
    )

    slug = models.SlugField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Nashr qilingan URL identifikatori",
    )

    published_revision = models.ForeignKey(
        "universities.UniversityTranslationRevision",
        on_delete=models.PROTECT,
        related_name="published_for_translations",
        null=True,
        blank=True,
        verbose_name="Joriy nashr qilingan versiya",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Universitet tarjimasi"
        verbose_name_plural = "Universitet tarjimalari"
        ordering = ["university", "language_code"]
        constraints = [
            models.UniqueConstraint(
                fields=["university", "language_code"],
                name="unique_university_language",
            ),
            models.UniqueConstraint(
                fields=["language_code", "slug"],
                name="unique_university_slug_per_language",
            ),
        ]

    def __str__(self):
        return f"{self.university_id} ({self.language_code})"


class UniversityTranslationRevision(models.Model):
    """Tarjima matnining versiyalarini, tasdiqlash va nashr tarixini saqlaydi."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Qoralama"
        REVIEW = "review", "Ko‘rib chiqilmoqda"
        PUBLISHED = "published", "Nashr qilingan"
        ARCHIVED = "archived", "Arxivlangan"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    translation = models.ForeignKey(
        UniversityTranslation,
        on_delete=models.PROTECT,
        related_name="revisions",
        verbose_name="Tarjima",
    )

    revision_number = models.PositiveIntegerField(
        verbose_name="Versiya raqami",
    )

    name = models.CharField(
        max_length=255,
        verbose_name="Universitet nomi",
    )
    slug = models.SlugField(
        max_length=255,
        verbose_name="URL identifikatori",
    )
    description = models.TextField(
        blank=True,
        verbose_name="Tavsif",
    )

    seo_title = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="SEO sarlavha",
    )
    seo_description = models.TextField(
        blank=True,
        verbose_name="SEO tavsifi",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
        verbose_name="Versiya holati",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_university_revisions",
        verbose_name="Yaratgan xodim",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="approved_university_revisions",
        null=True,
        blank=True,
        verbose_name="Tasdiqlagan xodim",
    )

    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Tasdiqlangan vaqt",
    )
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Nashr qilingan vaqt",
    )
    scheduled_publish_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Rejalashtirilgan nashr vaqti",
    )
    rejection_reason = models.TextField(
        blank=True,
        verbose_name="Rad etish sababi",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Universitet tarjimasi versiyasi"
        verbose_name_plural = "Universitet tarjimasi versiyalari"
        ordering = ["-revision_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["translation", "revision_number"],
                name="unique_translation_revision_number",
            ),
        ]
        indexes = [
            models.Index(
                fields=["translation", "status"],
                name="univ_revision_status_idx",
            ),
        ]

    def __str__(self):
        return f"{self.translation_id} / revision {self.revision_number}"


class UniversityAdmissionPeriod(models.Model):
    """Muayyan universitet versiyasiga tegishli qabul va o‘qish muddatlarini saqlaydi."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    university_revision = models.ForeignKey(
        UniversityRevision,
        on_delete=models.PROTECT,
        related_name="admission_periods",
        verbose_name="Universitet versiyasi",
    )

    name = models.CharField(
        max_length=150,
        verbose_name="Qabul davri nomi",
        help_text="Masalan: Spring 2027 yoki Fall 2027",
    )

    application_start_date = models.DateField(
        verbose_name="Ariza qabul qilish boshlanishi",
    )
    application_end_date = models.DateField(
        verbose_name="Ariza qabul qilish tugashi",
    )

    study_start_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="O‘qish boshlanishi",
    )
    study_end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="O‘qish tugashi",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Universitet qabul davri"
        verbose_name_plural = "Universitet qabul davrlari"
        ordering = ["-application_start_date"]
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    application_start_date__lte=F("application_end_date")
                ),
                name="valid_univ_application_dates",
            ),
            models.CheckConstraint(
                condition=(
                    Q(study_start_date__isnull=True)
                    | Q(study_end_date__isnull=True)
                    | Q(study_start_date__lte=F("study_end_date"))
                ),
                name="valid_univ_study_dates",
            ),
        ]
        indexes = [
            models.Index(
                fields=["university_revision", "application_start_date"],
                name="univ_admission_date_idx",
            ),
        ]

    def __str__(self):
        return f"{self.university_revision_id} / {self.name}"
