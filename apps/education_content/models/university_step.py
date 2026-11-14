import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class UniversityStep(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    page = models.ForeignKey(
        "education_content.UniversityStepPage",
        on_delete=models.CASCADE,
        related_name="steps",
    )

    step_number = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ],
    )
    dazhi_numeral = models.CharField(max_length=20)
    chinese_char = models.CharField(max_length=50)
    pinyin = models.CharField(max_length=100)
    chinese_concept = models.CharField(max_length=150)

    image = models.ImageField(
        upload_to="education/university_steps/",
    )

    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "University Step"
        verbose_name_plural = "University Steps"
        ordering = ("order", "step_number")
        constraints = [
            models.UniqueConstraint(
                fields=("page", "step_number"),
                name="unique_university_step_number",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    step_number__gte=1,
                    step_number__lte=5,
                ),
                name="university_step_number_range",
            ),
        ]
        indexes = [
            models.Index(
                fields=("page", "is_active", "order"),
                name="uni_step_page_active_idx",
            ),
        ]

    def __str__(self):
        return f"Step {self.step_number}: {self.chinese_char}"
