
from rest_framework.permissions import BasePermission

from apps.rbac.services.role_service import RoleService


def _has_role_permission(user, permission: str) -> bool:
    """
    Foydalanuvchining permissionini faqat role'lari orqali tekshiradi.
    """
    if (
        not user
        or not user.is_authenticated
        or not user.is_active
    ):
        return False

    if user.is_superuser:
        return True

    permissions = RoleService._get_actor_role_permissions(user)

    return permission in permissions


class CanManageRoles(BasePermission):
    """
    Faqat Superuser yoki role orqali rbac.manage_roles
    vakolatiga ega faol foydalanuvchilar kira oladi.
    """

    message = "Sizda rollarni boshqarish uchun yetarli ruxsat mavjud emas."

    def has_permission(self, request, view):
        return _has_role_permission(
            request.user,
            "rbac.manage_roles",
        )


class CanViewUsers(BasePermission):
    """
    Foydalanuvchilarni ko'rish uchun kerakli vakolatlarni tekshiradi.
    """

    message = "Foydalanuvchilarni ko‘rish uchun ruxsatingiz mavjud emas."

    def has_permission(self, request, view):
        user = request.user

        return (
            _has_role_permission(user, "rbac.manage_roles")
            and _has_role_permission(user, "users.view_user")
        )

