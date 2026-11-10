
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from apps.universities.models import (
    University,
    UniversityRevision,
    UniversityTranslation,
    UniversityTranslationRevision
)

User = get_user_model()


class UniversityService:
    """Universitet yaratish va uning global holatini boshqarish xizmatlari."""

    @staticmethod
    def _ensure_authenticated(actor: User) -> None:
        if not actor or not actor.is_authenticated:
            raise PermissionDenied(
                "Ushbu amal uchun autentifikatsiya talab qilinadi."
            )

    @staticmethod
    def _ensure_permission(actor: User, permission: str) -> None:
        UniversityService._ensure_authenticated(actor)

        if not actor.is_superuser and not actor.has_perm(
                f"universities.{permission}"
        ):
            raise PermissionDenied(
                "Ushbu amalni bajarish uchun ruxsatingiz mavjud emas."
            )


    @staticmethod
    @transaction.atomic
    def create_university(
        *,
        actor: User,
        city: str,
        country: str,
    ) -> University:
        """Universitet va uning birinchi revisionini atomik yaratadi."""

        UniversityService._ensure_permission(
            actor,
            "add_university",
        )

        city = city.strip()
        country = country.strip()

        if not city:
            raise ValidationError({"city": "Shahar nomi kiritilishi shart."})

        if not country:
            raise ValidationError({"country": "Mamlakat nomi kiritilishi shart."})

        university = University.objects.create(
            status=University.Status.DRAFT,
            created_by=actor,
            updated_by=actor,
        )

        UniversityRevision.objects.create(
            university=university,
            revision_number=1,
            city=city,
            country=country,
            status=UniversityRevision.Status.DRAFT,
            created_by=actor,
        )

        return university


    ALLOWED_STATUS_TRANSITIONS = {
        University.Status.DRAFT: {
            University.Status.REVIEW,
        },
        University.Status.REVIEW: {
            University.Status.DRAFT,
            University.Status.PUBLISHED,
        },
        University.Status.PUBLISHED: {
            University.Status.DRAFT,
            University.Status.ARCHIVED,
        },
        University.Status.ARCHIVED: {
            University.Status.DRAFT,
        },
    }


    STATUS_TRANSITION_PERMISSIONS = {
        (University.Status.DRAFT, University.Status.REVIEW):
            "submit_review_university",

        (University.Status.REVIEW, University.Status.DRAFT):
            "reject_university",

        (University.Status.REVIEW, University.Status.PUBLISHED):
            "publish_university",

        (University.Status.PUBLISHED, University.Status.DRAFT):
            "change_university",

        (University.Status.PUBLISHED, University.Status.ARCHIVED):
            "change_university",

        (University.Status.ARCHIVED, University.Status.DRAFT):
            "change_university",
    }


    @staticmethod
    @transaction.atomic
    def change_status(*, actor: User, university_id, new_status: str,) -> University:

        UniversityService._ensure_authenticated(actor)

        allowed_statuses = {
            University.Status.DRAFT,
            University.Status.REVIEW,
            University.Status.PUBLISHED,
            University.Status.ARCHIVED,
        }

        if new_status not in allowed_statuses:
            raise ValidationError({
                "status": "Noto‘g‘ri universitet statusi."
            })

        university = (
            University.objects
            .select_for_update()
            .filter(pk=university_id)
            .first()
        )

        if university is None:
            raise ValidationError("Universitet topilmadi.")

        if university.status == new_status:
            raise ValidationError(
                "Universitet allaqachon ushbu statusda."
            )

        allowed_statuses = (
            UniversityService.ALLOWED_STATUS_TRANSITIONS.get(
                university.status,
                set(),
            )
        )

        if new_status not in allowed_statuses:
            raise ValidationError({
                "status": (
                    f"{university.status} holatidan "
                    f"{new_status} holatiga o'tish mumkin emas."
                )
            })

        required_permission = (
            UniversityService.STATUS_TRANSITION_PERMISSIONS.get(
                (university.status, new_status)
            )
        )

        if required_permission is None:
            raise ValidationError(
                "Ushbu status o'zgarishi uchun permission belgilanmagan."
            )

        UniversityService._ensure_permission(
            actor,
            required_permission,
        )


        if new_status == University.Status.PUBLISHED:
            if university.published_revision_id is None:
                raise ValidationError(
                    "Universitetning nashr qilingan revisioni mavjud emas."
                )

            if (
                    university.published_revision.status
                    != UniversityRevision.Status.PUBLISHED
            ):
                raise ValidationError(
                    "Universitetning faol revisioni PUBLISHED holatida emas."
                )

            has_published_translation = (
                UniversityTranslation.objects
                .filter(
                    university_id=university.pk,
                    published_revision__isnull=False,
                    published_revision__status=(
                        UniversityTranslationRevision.Status.PUBLISHED
                    ),
                )
                .exists()
            )

            if not has_published_translation:
                raise ValidationError(
                    "Kamida bitta nashr qilingan tarjima mavjud bo'lishi shart."
                )

        university.status = new_status
        university.updated_by = actor

        university.save(
            update_fields=[
                "status",
                "updated_by",
                "updated_at",
            ]
        )

        return university
