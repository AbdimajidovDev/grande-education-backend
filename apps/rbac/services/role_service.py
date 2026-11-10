
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)
from django.db import IntegrityError, transaction

from django.contrib.auth import get_user_model

User = get_user_model()



class RoleService:
    """
    Handles role creation and role-related business rules.
    """

    @staticmethod
    def _is_role_name_unique_violation(exc: IntegrityError) -> bool:
        cause = exc.__cause__ or exc

        constraint_name = getattr(
            getattr(cause, "diag", None),
            "constraint_name",
            None,
        )

        if constraint_name in {
            "auth_group_name_lower_uniq",
            "auth_group_name_key",
        }:
            return True

        error_message = str(cause)

        return (
                "auth_group_name_lower_uniq" in error_message
                or "UNIQUE constraint failed: auth_group.name" in error_message
        )

    @staticmethod
    def _get_actor_role_permissions(actor) -> set[str]:
        """
        Foydalanuvchining faqat role'lar orqali olgan
        permissionlarini qaytaradi.
        """
        permissions = (
            actor.groups
            .values_list(
                "permissions__content_type__app_label",
                "permissions__codename",
            )
        )

        return {
            f"{app_label}.{codename}"
            for app_label, codename in permissions
            if app_label and codename
        }

    @staticmethod
    def _ensure_can_manage_roles(actor) -> None:
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

        if "rbac.manage_roles" not in actor_permissions:
            raise PermissionDenied(
                "Rollarni boshqarish huquqingiz mavjud emas."
            )


    @staticmethod
    @transaction.atomic
    def create_role(*, name: str, actor) -> Group:
        """
        Create a new role.

        Only users with roles.manage_roles permission
        or superusers can create roles.
        """

        RoleService._ensure_can_manage_roles(actor)

        name = name.strip()

        if not name:
            raise ValidationError({
                "name": "Role name cannot be empty."
            })

        if Group.objects.filter(name__iexact=name).exists():
            raise ValidationError({
                "name": "A role with this name already exists."
            })

        try:
            return Group.objects.create(name=name)

        except IntegrityError as exc:
            if RoleService._is_role_name_unique_violation(exc):
                raise ValidationError({
                    "name": "Bunday nomdagi rol allaqachon mavjud."
                }) from exc

            raise


    @staticmethod
    @transaction.atomic
    def update_role(*, role_id: int, name: str, actor) -> Group:
        RoleService._ensure_can_manage_roles(actor)

        name = name.strip()

        if not name:
            raise ValidationError({
                "name": "Role name cannot be empty."
            })

        try:
            role = Group.objects.select_for_update().get(pk=role_id)
        except Group.DoesNotExist:
            raise ValidationError({
                "role": "Role does not exist."
            })

        duplicate_exists = Group.objects.filter(
            name__iexact=name
        ).exclude(pk=role.pk).exists()

        if duplicate_exists:
            raise ValidationError({
                "name": "A role with this name already exists."
            })

        role.name = name

        try:
            role.save(update_fields=["name"])

        except IntegrityError as exc:
            if RoleService._is_role_name_unique_violation(exc):
                raise ValidationError({
                    "name": "Bunday nomdagi rol allaqachon mavjud."
                }) from exc

            raise

        return role



    @staticmethod
    @transaction.atomic
    def delete_role(*, role_id: int, actor) -> None:
        RoleService._ensure_can_manage_roles(actor)

        try:
            role = Group.objects.select_for_update().get(pk=role_id)
        except Group.DoesNotExist:
            raise ValidationError({
                "role": "Role does not exist."
            })

        if role.user_set.exists():
            raise ValidationError({
                "role": (
                    "Cannot delete a role assigned to users. "
                    "Reassign users before deleting this role."
                )
            })

        role.delete()



    @staticmethod
    @transaction.atomic
    def assign_permissions(
        *,
        role_id: int,
        permission_ids: list[int],
        actor,
    ) -> Group:

        RoleService._ensure_can_manage_roles(actor)

        role = Group.objects.select_for_update().filter(
            pk=role_id
        ).first()

        if role is None:
            raise ValidationError({
                "role": "Role does not exist."
            })

        if not permission_ids:
            return role

        unique_ids = set(permission_ids)

        permissions = list(
            Permission.objects.filter(id__in=unique_ids)
            .select_related("content_type")
        )

        if len(permissions) != len(unique_ids):
            raise ValidationError({
                "permissions": "One or more permissions do not exist."
            })


        if actor.is_superuser:
            role.permissions.add(*permissions)
            return role

        if any(
            permission.content_type.app_label == "rbac"
            and permission.codename == "manage_roles"
            for permission in permissions
        ):
            raise PermissionDenied(
                "Only superusers can grant role management permission."
            )

        actor_permissions = RoleService._get_actor_role_permissions(actor)

        unauthorized = [
            permission
            for permission in permissions
            if (
                f"{permission.content_type.app_label}."
                f"{permission.codename}"
            ) not in actor_permissions
        ]

        if unauthorized:
            raise PermissionDenied(
                "You cannot assign permissions you do not possess."
            )

        role.permissions.add(*permissions)

        return role



    @staticmethod
    @transaction.atomic
    def remove_permissions(
        *,
        role_id: int,
        permission_ids: list[int],
        actor,
    ) -> Group:
        RoleService._ensure_can_manage_roles(actor)

        role = Group.objects.select_for_update().filter(
            pk=role_id
        ).first()

        if role is None:
            raise ValidationError({
                "role": "Role does not exist."
            })

        unique_ids = set(permission_ids)

        if not unique_ids:
            return role

        permissions = list(
            Permission.objects.filter(id__in=unique_ids)
            .select_related("content_type")
        )

        if len(permissions) != len(unique_ids):
            raise ValidationError({
                "permissions": "One or more permissions do not exist."
            })

        if actor.is_superuser:
            role.permissions.remove(*permissions)
            return role

        for permission in permissions:
            if (
                permission.content_type.app_label == "rbac"
                and permission.codename == "manage_roles"
            ):
                raise PermissionDenied(
                    "Only superusers can revoke role management permission."
                )

        actor_permissions = RoleService._get_actor_role_permissions(actor)

        unauthorized = [
            permission
            for permission in permissions
            if (
                f"{permission.content_type.app_label}."
                f"{permission.codename}"
            ) not in actor_permissions
        ]

        if unauthorized:
            raise PermissionDenied(
                "You cannot remove permissions you do not possess."
            )

        role.permissions.remove(*permissions)

        return role

    @staticmethod
    def _ensure_permission(actor: User, permission: str) -> None:
        if (
                actor is None
                or not actor.is_authenticated
                or not actor.is_active
        ):
            raise PermissionDenied(
                "Ushbu amalni bajarish uchun faol foydalanuvchi bo'lishingiz kerak."
            )

        if actor.is_superuser:
            return

        actor_permissions = RoleService._get_actor_role_permissions(actor)

        if f"users.{permission}" not in actor_permissions:
            raise PermissionDenied(
                "Ushbu amalni bajarish uchun ruxsatingiz mavjud emas."
            )

    @staticmethod
    @transaction.atomic
    def remove_employee_from_roles(
            *,
            role_ids: list[int],
            employee,
            actor,
    ) -> list[Group]:
        """Xodimdan bir yoki bir nechta rolni olib tashlaydi."""

        # 1. Actor vakolatini tekshirish.
        if (
                actor is None
                or not actor.is_authenticated
                or not actor.is_active
        ):
            raise PermissionDenied(
                "Bu amalni bajarish uchun faol foydalanuvchi bo'lishingiz kerak."
            )

        if not actor.is_superuser:
            actor_permissions = RoleService._get_actor_role_permissions(actor)

            if "users.assign_roles" not in actor_permissions:
                raise PermissionDenied(
                    "Xodimlarning rollarini boshqarish huquqingiz mavjud emas."
                )

        # 2. Xodimni tekshirish.
        if (
                employee is None
                or employee.pk is None
                or employee.is_staff
                or employee.is_superuser
        ):
            raise ValidationError({
                "employee": "Bu foydalanuvchining rollarini o'zgartirib bo'lmaydi."
            })

        # 3. Takroriy ID larni tekshirish.
        if len(role_ids) != len(set(role_ids)):
            raise ValidationError({
                "role_ids": "Rol ID raqamlari takrorlanmasligi kerak."
            })

        if not role_ids:
            return []

        # 4. Rollarni olish.
        roles = list(
            Group.objects
            .select_for_update()
            .filter(pk__in=role_ids)
            .order_by("id")
        )

        if len(roles) != len(role_ids):
            raise ValidationError({
                "role_ids": "Ko'rsatilgan rollardan biri yoki bir nechtasi mavjud emas."
            })

        locked_employee = (
            User.objects
            .select_for_update()
            .filter(
                pk=employee.pk,
                is_staff=False,
                is_superuser=False,
            )
            .first()
        )

        if locked_employee is None:
            raise ValidationError({
                "employee": "Xodim topilmadi yoki uning rollarini o'zgartirib bo'lmaydi."
            })

        # 5. Xodimga biriktirilgan rollarni tekshirish.
        assigned_role_ids = set(
            locked_employee.groups.filter(
                pk__in=role_ids
            ).values_list("id", flat=True)
        )

        if assigned_role_ids != set(role_ids):
            raise ValidationError({
                "role_ids": "Ko'rsatilgan rollardan biri yoki bir nechtasi xodimga biriktirilmagan."
            })

        # 6. Rollarni olib tashlash.
        locked_employee.groups.remove(*roles)

        return roles

