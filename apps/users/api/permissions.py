from rest_framework.permissions import BasePermission
from apps.rbac.services.role_service import RoleService


class BaseEmployeePermission(BasePermission):
    permission_codename = None

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated or not user.is_active:
            return False

        if user.is_superuser:
            return True

        if not self.permission_codename:
            return False

        user_permissions = RoleService._get_actor_role_permissions(user)

        return f"users.{self.permission_codename}" in user_permissions


class CanViewEmployees(BaseEmployeePermission):
    permission_codename = "view_user"
    message = "Xodimlarni ko‘rish uchun ruxsatingiz mavjud emas."


class CanCreateEmployees(BaseEmployeePermission):
    permission_codename = "add_user"
    message = "Xodim yaratish uchun ruxsatingiz mavjud emas."


class CanUpdateEmployees(BaseEmployeePermission):
    permission_codename = "change_user"
    message = "Xodim ma'lumotlarini tahrirlash uchun ruxsatingiz mavjud emas."


class CanManageEmployeeStatus(BaseEmployeePermission):
    permission_codename = "change_user"
    message = "Xodim statusini boshqarish uchun ruxsatingiz mavjud emas."


class CanAssignEmployeeRoles(BaseEmployeePermission):
    permission_codename = "assign_roles"

    message = "Xodimlarning rollarini boshqarish huquqingiz mavjud emas."