from rest_framework.permissions import BasePermission

from apps.rbac.services.role_service import RoleService


class CanViewDashboard(BasePermission):
    message = "You do not have permission to view the dashboard."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        # Superuser har doim ruxsatga ega.
        if user.is_superuser:
            return True

        # Boshqa rollar uchun maxsus permission tekshiriladi.
        permissions = RoleService._get_actor_role_permissions(user)

        return "dashboard.view_dashboard" in permissions
    