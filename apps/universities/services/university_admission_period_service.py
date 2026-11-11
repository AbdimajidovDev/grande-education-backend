
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction

from apps.rbac.services.role_service import RoleService
from apps.universities.models import (
    University,
    UniversityRevision,
    UniversityAdmissionPeriod,
)


User = get_user_model()


class UniversityAdmissionPeriodService:
    """Universitet qabul davrlarini boshqaradi."""

    EDITABLE_FIELDS = {
        "name",
        "application_start_date",
        "application_end_date",
        "study_start_date",
        "study_end_date",
    }

    @staticmethod
    def _ensure_permission(actor: User, permission: str) -> None:
        if (
            actor is None
            or not actor.is_authenticated
            or not actor.is_active
        ):
            raise PermissionDenied(
                "Bu amalni bajarish uchun faol foydalanuvchi "
                "bo'lishingiz kerak."
            )

        if actor.is_superuser:
            return

        actor_permissions = RoleService._get_actor_role_permissions(actor)

        if f"universities.{permission}" not in actor_permissions:
            raise PermissionDenied(
                "Ushbu amalni bajarish uchun ruxsatingiz mavjud emas."
            )

    @staticmethod
    def _get_revision_for_update(revision_id) -> UniversityRevision:
        """University va revisionni yagona lock tartibida oladi."""

        university_id = (
            UniversityRevision.objects
            .filter(pk=revision_id)
            .values_list("university_id", flat=True)
            .first()
        )

        if university_id is None:
            raise ValidationError("Universitet revisioni topilmadi.")

        university = (
            University.objects
            .select_for_update()
            .filter(pk=university_id)
            .first()
        )

        if university is None:
            raise ValidationError("Universitet topilmadi.")

        if university.status == University.Status.ARCHIVED:
            raise ValidationError(
                "Arxivlangan universitet qabul davrlarini "
                "boshqarish mumkin emas."
            )

        revision = (
            UniversityRevision.objects
            .select_for_update()
            .filter(
                pk=revision_id,
                university_id=university.pk,
            )
            .first()
        )

        if revision is None:
            raise ValidationError("Universitet revisioni topilmadi.")

        if revision.status != UniversityRevision.Status.DRAFT:
            raise ValidationError(
                "Qabul davrlarini faqat DRAFT revisionda "
                "boshqarish mumkin."
            )

        revision.university = university
        return revision

    @staticmethod
    def _validate_dates(data: dict) -> None:
        application_start = data.get("application_start_date")
        application_end = data.get("application_end_date")
        study_start = data.get("study_start_date")
        study_end = data.get("study_end_date")

        if application_start is None:
            raise ValidationError({
                "application_start_date": "Ariza boshlanish sanasi kiritilishi shart."
            })

        if application_end is None:
            raise ValidationError({
                "application_end_date": "Ariza tugash sanasi kiritilishi shart."
            })

        if application_start > application_end:
            raise ValidationError({
                "application_end_date": (
                    "Ariza tugash sanasi boshlanish sanasidan "
                    "oldin bo'lishi mumkin emas."
                )
            })

        if (
            study_start is not None
            and study_end is not None
            and study_start > study_end
        ):
            raise ValidationError({
                "study_end_date": (
                    "O'qish tugash sanasi boshlanish sanasidan "
                    "oldin bo'lishi mumkin emas."
                )
            })

    @staticmethod
    def _normalize_name(name: str) -> str:
        name = name.strip()

        if not name:
            raise ValidationError({
                "name": "Qabul davri nomi kiritilishi shart."
            })

        if not isinstance(name, str) or not name.strip():
            raise ValidationError({
                "name": "Qabul davri nomi kiritilishi shart."
            })

        return name.strip()


    @staticmethod
    @transaction.atomic
    def create_period(
        *,
        actor: User,
        revision_id,
        name: str,
        application_start_date,
        application_end_date,
        study_start_date=None,
        study_end_date=None,
    ) -> UniversityAdmissionPeriod:
        """DRAFT revision uchun yangi qabul davri yaratadi."""

        UniversityAdmissionPeriodService._ensure_permission(
            actor,
            "change_university",
        )

        revision = (
            UniversityAdmissionPeriodService._get_revision_for_update(
                revision_id
            )
        )

        name = UniversityAdmissionPeriodService._normalize_name(name)

        period_data = {
            "application_start_date": application_start_date,
            "application_end_date": application_end_date,
            "study_start_date": study_start_date,
            "study_end_date": study_end_date,
        }

        UniversityAdmissionPeriodService._validate_dates(period_data)

        try:
            return UniversityAdmissionPeriod.objects.create(
                university_revision=revision,
                name=name,
                **period_data,
            )
        except IntegrityError as exc:
            raise ValidationError(
                "Qabul davrini yaratishda ma'lumotlar to'qnashuvi yuz berdi."
            ) from exc

    @staticmethod
    @transaction.atomic
    def update_period(
        *,
        actor: User,
        period_id,
        data: dict,
    ) -> UniversityAdmissionPeriod:
        """DRAFT revisionga tegishli qabul davrini qisman tahrirlaydi."""

        UniversityAdmissionPeriodService._ensure_permission(
            actor,
            "change_university",
        )

        if not data:
            raise ValidationError("Tahrirlash uchun ma'lumot yuborilmadi.")

        unknown_fields = set(data) - (
            UniversityAdmissionPeriodService.EDITABLE_FIELDS
        )

        if unknown_fields:
            raise ValidationError({
                "fields": (
                    "Noma'lum yoki tahrirlash mumkin bo'lmagan maydonlar: "
                    f"{', '.join(sorted(unknown_fields))}"
                )
            })

        revision_id = (
            UniversityAdmissionPeriod.objects
            .filter(pk=period_id)
            .values_list("university_revision_id", flat=True)
            .first()
        )

        if revision_id is None:
            raise ValidationError("Qabul davri topilmadi.")

        revision = (
            UniversityAdmissionPeriodService._get_revision_for_update(
                revision_id
            )
        )

        period = (
            UniversityAdmissionPeriod.objects
            .select_for_update()
            .filter(
                pk=period_id,
                university_revision_id=revision.pk,
            )
            .first()
        )

        if period is None:
            raise ValidationError("Qabul davri topilmadi.")

        if "name" in data:
            data["name"] = (
                UniversityAdmissionPeriodService._normalize_name(
                    data["name"]
                )
            )

        merged_data = {
            field: data.get(field, getattr(period, field))
            for field in (
                "application_start_date",
                "application_end_date",
                "study_start_date",
                "study_end_date",
            )
        }

        UniversityAdmissionPeriodService._validate_dates(merged_data)

        for field, value in data.items():
            setattr(period, field, value)

        try:
            period.save(update_fields=[*data.keys(), "updated_at"])
        except IntegrityError as exc:
            raise ValidationError(
                "Qabul davrini yangilashda ma'lumotlar to'qnashuvi yuz berdi."
            ) from exc

        return period

    @staticmethod
    @transaction.atomic
    def delete_period(
        *,
        actor: User,
        period_id,
    ) -> None:
        """DRAFT revisionga tegishli qabul davrini o'chiradi."""

        UniversityAdmissionPeriodService._ensure_permission(
            actor,
            "change_university",
        )

        revision_id = (
            UniversityAdmissionPeriod.objects
            .filter(pk=period_id)
            .values_list("university_revision_id", flat=True)
            .first()
        )

        if revision_id is None:
            raise ValidationError("Qabul davri topilmadi.")

        revision = (
            UniversityAdmissionPeriodService._get_revision_for_update(
                revision_id
            )
        )

        period = (
            UniversityAdmissionPeriod.objects
            .select_for_update()
            .filter(
                pk=period_id,
                university_revision_id=revision.pk,
            )
            .first()
        )

        if period is None:
            raise ValidationError("Qabul davri topilmadi.")

        period.delete()
