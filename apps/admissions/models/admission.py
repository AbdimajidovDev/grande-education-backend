
import uuid

from django.conf import settings
from django.db import models


class Admission(models.Model):
    """
    Talabaning Xitoy universitetiga qabul jarayonini boshqaradi.
    """

    class Stage(models.TextChoices):
        CONSULTATION = "CONSULTATION", "Dastlabki konsultatsiya"
        SELECTION = "SELECTION", "OTM va yo'nalish tanlash"
        EXAMS = "EXAMS", "Imtihonlar va HSK"
        DOCUMENTS = "DOCUMENTS", "Hujjatlar va viza"
        ARRIVAL = "ARRIVAL", "Xitoyga yetib borish"
        CANCELLED = "CANCELLED", "Bekor qilingan"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    # Saytdan kelgan murojaat. Ofisdan kelgan talabada null bo'lishi mumkin.
    inquiry = models.ForeignKey(
        "inquiries.Inquiry",
        on_delete=models.SET_NULL,
        related_name="admissions",
        null=True,
        blank=True,
    )

    # Talabaning shaxsiy ma'lumotlari.
    full_name = models.CharField(
        max_length=255,
    )

    passport_full_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    phone_number = models.CharField(
        max_length=20,
    )

    email = models.EmailField(
        blank=True,
        default="",
    )

    # Qabul jarayonida tanlangan ta'lim ma'lumotlari.
    university = models.ForeignKey(
        "universities.University",
        on_delete=models.PROTECT,
        related_name="admissions",
        null=True,
        blank=True,
    )

    program = models.ForeignKey(
        "programs.Program",
        on_delete=models.PROTECT,
        related_name="admissions",
        null=True,
        blank=True,
    )

    direction = models.ForeignKey(
        "directions.Direction",
        on_delete=models.PROTECT,
        related_name="admissions",
        null=True,
        blank=True,
    )

    hsk_level = models.CharField(
        max_length=20,
        blank=True,
        default="",
    )

    # Qabul jarayonining joriy bosqichi.
    stage = models.CharField(
        max_length=20,
        choices=Stage.choices,
        default=Stage.CONSULTATION,
        db_index=True,
    )

    # Mas'ul kurator.
    curator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="curated_admissions",
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "admissions"
        verbose_name = "Admission"
        verbose_name_plural = "Admissions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["stage", "created_at"],
                name="admission_stage_created_idx",
            ),
            models.Index(
                fields=["curator", "stage"],
                name="admission_curator_stage_idx",
            ),
        ]
        permissions = [
            (
                "view_all_admissions",
                "Can view all admissions",
            ),
            (
                "change_admission_stage",
                "Can change admission stage",
            ),
            (
                "override_admission_stage_transition",
                "Can override admission stage transition rules",
            ),
            (
                "assign_admission_curator",
                "Can assign admission curator",
            ),
            (
                "cancel_admission",
                "Can cancel admission",
            ),
            (
                "restore_admission",
                "Can restore admission",
            ),
            (
                "add_admission_comment",
                "Can add admission comment",
            ),

        ]


    def __str__(self):
        return f"{self.full_name} - {self.stage}"

