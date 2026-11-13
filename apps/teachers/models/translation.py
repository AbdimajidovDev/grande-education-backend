
import uuid

from django.db import models


class TeacherTranslation(models.Model):

    class Language(models.TextChoices):
        UZ = "uz", "Uzbek"
        RU = "ru", "Russian"
        EN = "en", "English"
        ZH = "zh", "Chinese"
        JA = "ja", "Japanese"
        DE = "de", "German"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, )
    teacher = models.ForeignKey("teachers.Teacher", on_delete=models.CASCADE, related_name="translations",)
    language_code = models.CharField(max_length=2, choices=Language.choices,)
    role = models.CharField(max_length=255,)
    experience = models.CharField(max_length=255, )
    bio = models.TextField()

    skills = models.JSONField(default=list, blank=True, )

    class Meta:
        verbose_name = "Teacher Translation"
        verbose_name_plural = "Teacher Translations"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    language_code__in=["uz", "ru", "en", "zh", "ja", "de"]
                ),
                name="valid_teacher_language",
            ),
        ]

    def __str__(self):
        return f"{self.teacher.full_name} ({self.language_code})"

