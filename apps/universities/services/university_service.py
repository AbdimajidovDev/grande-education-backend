
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from apps.rbac.services.role_service import RoleService

from apps.universities.models import (
    University,
    UniversityRevision,
)

User = get_user_model()


class UniversityService:
    """Universitet yaratish va uning global holatini boshqarish xizmatlari."""

    @staticmethod
    def _ensure_authenticated(actor: User) -> None:
        if (
                actor is None
                or not actor.is_authenticated
                or not actor.is_active
        ):
            raise PermissionDenied(
                "Bu amalni bajarish uchun faol foydalanuvchi "
                "bo'lishingiz kerak."
            )

    @staticmethod
    def _ensure_permission(actor: User, permission: str) -> None:
        UniversityService._ensure_authenticated(actor)

        if actor.is_superuser:
            return

        actor_permissions = RoleService._get_actor_role_permissions(actor)

        if f"universities.{permission}" not in actor_permissions:
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
        University.Status.PUBLISHED: {
            University.Status.ARCHIVED,
        },
        University.Status.ARCHIVED: {
            University.Status.DRAFT,
        },
    }

    STATUS_TRANSITION_PERMISSIONS = {
        (
            University.Status.PUBLISHED,
            University.Status.ARCHIVED,
        ): "change_university",

        (
            University.Status.ARCHIVED,
            University.Status.DRAFT,
        ): "change_university",
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
