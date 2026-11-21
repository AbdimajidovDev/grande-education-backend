
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from apps.rbac.services.role_service import RoleService
from apps.universities.models import (
    University,
    UniversityRevision,
    UniversityMedia,
)

User = get_user_model()


class UniversityMediaService:
    """Universitet media fayllarini (logo, cover, gallery) boshqaradi."""

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
                "Arxivlangan universitet media fayllarini boshqarish mumkin emas."
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
                "Media fayllarni faqat DRAFT revisionda boshqarish mumkin."
            )

        revision.university = university
        return revision

    @staticmethod
    @transaction.atomic
    def create_media(
        *,
        actor: User,
        revision_id,
        file,
        media_type: str = UniversityMedia.MediaType.GALLERY,
        order: int = 0,
        caption: str = "",
    ) -> UniversityMedia:
        """DRAFT revision uchun yangi media fayl yuklaydi."""

        UniversityMediaService._ensure_permission(
            actor,
            "add_universitymedia",
        )

        if not file:
            raise ValidationError({"file": "Media fayl yuklanishi shart."})

        if media_type not in UniversityMedia.MediaType.values:
            raise ValidationError({
                "media_type": f"Noto'g'ri media turi: {media_type}"
            })

        revision = UniversityMediaService._get_revision_for_update(revision_id)

        caption = caption.strip() if caption else ""

        # Agar logo yoki cover bo'lsa, avvalgilarining o'rnini almashtirish mumkin
        media = UniversityMedia.objects.create(
            university_revision=revision,
            file=file,
            media_type=media_type,
            order=order,
            caption=caption,
        )

        return media

    @staticmethod
    @transaction.atomic
    def update_media(
        *,
        actor: User,
        media_id,
        media_type: str | None = None,
        order: int | None = None,
        caption: str | None = None,
    ) -> UniversityMedia:
        """Media fayl metama'lumotlarini yangilaydi."""

        UniversityMediaService._ensure_permission(
            actor,
            "change_universitymedia",
        )

        media = (
            UniversityMedia.objects
            .select_for_update()
            .filter(pk=media_id)
            .first()
        )

        if media is None:
            raise ValidationError("Media fayl topilmadi.")

        revision = UniversityMediaService._get_revision_for_update(
            media.university_revision_id
        )

        update_fields = []

        if media_type is not None:
            if media_type not in UniversityMedia.MediaType.values:
                raise ValidationError({
                    "media_type": f"Noto'g'ri media turi: {media_type}"
                })
            media.media_type = media_type
            update_fields.append("media_type")

        if order is not None:
            media.order = order
            update_fields.append("order")

        if caption is not None:
            media.caption = caption.strip()
            update_fields.append("caption")

        if update_fields:
            update_fields.append("updated_at")
            media.save(update_fields=update_fields)

        return media

    @staticmethod
    @transaction.atomic
    def delete_media(*, actor: User, media_id) -> None:
        """Media faylni o'chiradi va diskdan tozalaydi."""

        UniversityMediaService._ensure_permission(
            actor,
            "delete_universitymedia",
        )

        media = (
            UniversityMedia.objects
            .select_for_update()
            .filter(pk=media_id)
            .first()
        )

        if media is None:
            raise ValidationError("Media fayl topilmadi.")

        revision = UniversityMediaService._get_revision_for_update(
            media.university_revision_id
        )

        file_obj = media.file

        def _cleanup_storage_file():
            try:
                if file_obj:
                    file_obj.delete(save=False)
            except Exception:
                pass

        transaction.on_commit(_cleanup_storage_file)
        media.delete()
