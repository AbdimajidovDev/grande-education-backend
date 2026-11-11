
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction

from apps.rbac.services.role_service import RoleService
from apps.universities.models import FAQ


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

        if order is not None:
            if order < 0:
                raise ValidationError({
                    "order": "Tartib raqami manfiy bo'lishi mumkin emas."
                })

            faq.order = order
            update_fields.append("order")

        if is_active is not None:
            faq.is_active = is_active
            update_fields.append("is_active")

        if update_fields:
            update_fields.append("updated_at")
            faq.save(update_fields=update_fields)

        return faq
