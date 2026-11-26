
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError

from apps.rbac.services.role_service import RoleService
from apps.universities.models import (
    FAQ,
    FAQTranslation,
    FAQTranslationRevision,
    UniversityAuditLog,
)
from apps.universities.services.audit_log_service import AuditLogService
from apps.universities.services.exceptions import ResourceNotFoundError


User = get_user_model()


class FAQService:
    """FAQ obyektlarini boshqarish xizmatlari."""

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
    @transaction.atomic
    def create_faq(*, actor: User, order: int = 0) -> FAQ:
        """Yangi FAQ obyektini yaratadi."""

        FAQService._ensure_permission(actor, "add_faq")

        if order < 0:
            raise ValidationError({
                "order": "Tartib raqami manfiy bo'lishi mumkin emas."
            })

        return FAQ.objects.create(
            order=order,
            is_active=True,
        )

    @staticmethod
    @transaction.atomic
    def update_faq(
        *,
        actor: User,
        faq_id,
        order: int | None = None,
        is_active: bool | None = None,
    ) -> FAQ:
        """FAQ tartibi va faollik holatini yangilaydi."""

        FAQService._ensure_permission(actor, "change_faq")

        if order is None and is_active is None:
            raise ValidationError(
                "Yangilash uchun kamida bitta maydon yuborilishi kerak."
            )

        faq = (
            FAQ.objects
            .select_for_update()
            .filter(pk=faq_id)
            .first()
        )

        if faq is None:
            raise ValidationError("FAQ topilmadi.")

        update_fields = []
        archived_now = False

        if order is not None:
            if order < 0:
                raise ValidationError({
                    "order": "Tartib raqami manfiy bo'lishi mumkin emas."
                })

            faq.order = order
            update_fields.append("order")

        if is_active is not None:
            if faq.is_active and not is_active:
                archived_now = True
            faq.is_active = is_active
            update_fields.append("is_active")

        if update_fields:
            update_fields.append("updated_at")
            faq.save(update_fields=update_fields)

        if archived_now:
            AuditLogService.log_archives(
                actor=actor,
                entries=[
                    {
                        "object_type": UniversityAuditLog.ObjectType.FAQ,
                        "object_id": faq.pk,
                        "object_repr": f"FAQ {faq.pk}",
                        "metadata": {
                            "previous_is_active": True,
                            "new_is_active": False,
                        },
                    }
                ],
            )

        return faq

    @staticmethod
    @transaction.atomic
    def delete_faq(*, actor: User, faq_id) -> None:
        """Faqat faolsizlantirilgan va barcha reviziyalari ARCHIVED bo'lgan FAQni o'chiradi."""

        FAQService._ensure_permission(actor, "delete_faq")

        faq = (
            FAQ.objects
            .select_for_update()
            .filter(pk=faq_id)
            .first()
        )

        if faq is None:
            raise ResourceNotFoundError("FAQ topilmadi.")

        if faq.is_active:
            raise ValidationError(
                "Faqat faolsizlantirilgan (arxivlangan) FAQni o'chirish mumkin."
            )

        translations = list(
            FAQTranslation.objects
            .select_for_update()
            .filter(faq=faq)
            .order_by("id")
        )
        translation_ids = [translation.id for translation in translations]

        revisions = []
        if translation_ids:
            revisions = list(
                FAQTranslationRevision.objects
                .select_for_update()
                .filter(translation_id__in=translation_ids)
                .order_by("id")
            )

        if any(
            translation.published_revision_id is not None
            for translation in translations
        ):
            raise ValidationError(
                "Nashr qilingan tarjima bog'lanishiga ega FAQni "
                "o'chirish mumkin emas."
            )

        if any(
            revision.status != FAQTranslationRevision.Status.ARCHIVED
            for revision in revisions
        ):
            raise ValidationError(
                "FAQ tarkibida ARCHIVED bo'lmagan reviziya mavjud."
            )

        audit_entries = [
            {
                "object_type": UniversityAuditLog.ObjectType.FAQ_TRANSLATION_REVISION,
                "object_id": revision.pk,
                "object_repr": f"{revision.question} (rev {revision.revision_number})",
                "metadata": {
                    "faq_id": str(faq.pk),
                    "translation_id": str(revision.translation_id),
                    "revision_number": revision.revision_number,
                    "status": revision.status,
                    "deleted_via": "FAQ",
                },
            }
            for revision in revisions
        ]
        for translation in translations:
            audit_entries.append({
                "object_type": UniversityAuditLog.ObjectType.FAQ_TRANSLATION,
                "object_id": translation.pk,
                "object_repr": f"FAQTranslation ({translation.language_code})",
                "metadata": {
                    "faq_id": str(faq.pk),
                    "language_code": translation.language_code,
                    "deleted_via": "FAQ",
                },
            })
        audit_entries.append({
            "object_type": UniversityAuditLog.ObjectType.FAQ,
            "object_id": faq.pk,
            "object_repr": f"FAQ {faq.pk}",
            "metadata": {
                "order": faq.order,
                "is_active": faq.is_active,
                "translations_count": len(translations),
            },
        })

        if translation_ids:
            FAQTranslation.objects.filter(faq=faq).update(
                published_revision=None,
            )
            FAQTranslationRevision.objects.filter(
                translation_id__in=translation_ids,
            ).delete()
            FAQTranslation.objects.filter(faq=faq).delete()

        try:
            faq.delete()
        except ProtectedError as exc:
            raise ValidationError(
                "FAQga bog'langan himoyalangan yozuvlar mavjudligi "
                "sababli uni o'chirish mumkin emas."
            ) from exc

        AuditLogService.log_deletes(actor=actor, entries=audit_entries)

