
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction

from apps.rbac.services.role_service import RoleService
from apps.universities.models import (
    University,
    UniversityRevision,
    UniversityMajor,
    UniversityMajorTranslation,
)
from apps.universities.constants import SUPPORTED_LANGUAGES

User = get_user_model()


class UniversityMajorService:
    """Universitet yo'nalishlarini (majors) va ularning tarjimalarini boshqaradi."""

    @staticmethod
    def _ensure_permission(actor: User, permission: str) -> None:
        if (
            actor is None
            or not actor.is_authenticated
            or not actor.is_active
        ):
            raise PermissionDenied(
                "Bu amalni bajarish uchun faol foydalanuvchi bo'lishingiz kerak."
            )

        if actor.is_superuser:
            return

        actor_permissions = RoleService._get_actor_role_permissions(actor)

        # Ruxsat yoki umbrella 'change_university' bo'lsa ruxsat beriladi
        has_perm = (
            f"universities.{permission}" in actor_permissions
            or "universities.change_university" in actor_permissions
        )

        if not has_perm:
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
                "Arxivlangan universitet yo'nalishlarini boshqarish mumkin emas."
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
                "Yo'nalishlarni faqat DRAFT revisionda boshqarish mumkin."
            )

        revision.university = university
        return revision

    @staticmethod
    @transaction.atomic
    def create_major(
        *,
        actor: User,
        revision_id,
        order: int = 0,
        is_active: bool = True,
        translations: list[dict] | None = None,
    ) -> UniversityMajor:
        """DRAFT revision uchun yangi yo'nalish yaratadi."""

        UniversityMajorService._ensure_permission(
            actor,
            "add_universitymajor",
        )

        revision = UniversityMajorService._get_revision_for_update(revision_id)

        major = UniversityMajor.objects.create(
            university_revision=revision,
            order=order,
            is_active=is_active,
        )

        if translations:
            for trans_data in translations:
                lang = trans_data.get("language_code", "").strip().lower()
                title = trans_data.get("title", "").strip()
                desc = trans_data.get("description", "").strip()

                if not lang or lang not in SUPPORTED_LANGUAGES:
                    raise ValidationError({
                        "language_code": f"Noto'g'ri til kodi: {lang}"
                    })

                if not title:
                    raise ValidationError({
                        "title": "Yo'nalish nomi kiritilishi shart."
                    })

                UniversityMajorTranslation.objects.create(
                    major=major,
                    language_code=lang,
                    title=title,
                    description=desc,
                )

        return major

    @staticmethod
    @transaction.atomic
    def update_major(
        *,
        actor: User,
        major_id,
        order: int | None = None,
        is_active: bool | None = None,
    ) -> UniversityMajor:
        """Yo'nalishning umumiy sozlamalarini tahrirlaydi."""

        UniversityMajorService._ensure_permission(
            actor,
            "change_universitymajor",
        )

        major = (
            UniversityMajor.objects
            .select_for_update()
            .filter(pk=major_id)
            .first()
        )

        if major is None:
            raise ValidationError("Yo'nalish topilmadi.")

        # Revisionni tekshirish
        revision = UniversityMajorService._get_revision_for_update(
            major.university_revision_id
        )

        update_fields = []
        if order is not None:
            major.order = order
            update_fields.append("order")

        if is_active is not None:
            major.is_active = is_active
            update_fields.append("is_active")

        if update_fields:
            update_fields.append("updated_at")
            major.save(update_fields=update_fields)

        return major

    @staticmethod
    @transaction.atomic
    def set_major_translation(
        *,
        actor: User,
        major_id,
        language_code: str,
        title: str,
        description: str = "",
    ) -> UniversityMajorTranslation:
        """Yo'nalish uchun muayyan tildagi tarjimani yaratadi yoki yangilaydi."""

        UniversityMajorService._ensure_permission(
            actor,
            "change_universitymajor",
        )

        major = (
            UniversityMajor.objects
            .select_for_update()
            .filter(pk=major_id)
            .first()
        )

        if major is None:
            raise ValidationError("Yo'nalish topilmadi.")

        revision = UniversityMajorService._get_revision_for_update(
            major.university_revision_id
        )

        language_code = language_code.strip().lower()
        title = title.strip()
        description = description.strip()

        if not language_code or language_code not in SUPPORTED_LANGUAGES:
            raise ValidationError({
                "language_code": f"Noto'g'ri til kodi: {language_code}"
            })

        if not title:
            raise ValidationError({
                "title": "Yo'nalish nomi kiritilishi shart."
            })

        trans, _ = UniversityMajorTranslation.objects.update_or_create(
            major=major,
            language_code=language_code,
            defaults={
                "title": title,
                "description": description,
            },
        )

        return trans

    @staticmethod
    @transaction.atomic
    def delete_major(*, actor: User, major_id) -> None:
        """Yo'nalishni o'chiradi."""

        UniversityMajorService._ensure_permission(
            actor,
            "delete_universitymajor",
        )

        major = (
            UniversityMajor.objects
            .select_for_update()
            .filter(pk=major_id)
            .first()
        )

        if major is None:
            raise ValidationError("Yo'nalish topilmadi.")

        revision = UniversityMajorService._get_revision_for_update(
            major.university_revision_id
        )

        major.delete()
