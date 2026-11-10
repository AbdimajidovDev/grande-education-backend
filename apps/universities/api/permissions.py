
from rest_framework.permissions import BasePermission

from apps.rbac.services.role_service import RoleService


class BaseUniversityPermission(BasePermission):
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

        return (
            f"universities.{self.permission_codename}"
            in user_permissions
        )


class CanViewUniversities(BaseUniversityPermission):
    permission_codename = "view_university"
    message = "Universitetlarni ko‘rish uchun ruxsatingiz mavjud emas."


class CanCreateUniversity(BaseUniversityPermission):
    permission_codename = "add_university"
    message = "Universitet yaratish uchun ruxsatingiz mavjud emas."


class CanUpdateUniversity(BaseUniversityPermission):
    permission_codename = "change_university"
    message = "Universitet ma'lumotlarini tahrirlash uchun ruxsatingiz mavjud emas."


class CanSubmitUniversityForReview(BaseUniversityPermission):
    permission_codename = "submit_review_university"
    message = "Universitetni ko‘rib chiqishga yuborish uchun ruxsatingiz mavjud emas."


class CanApproveUniversity(BaseUniversityPermission):
    permission_codename = "approve_university"
    message = "Universitetni tasdiqlash uchun ruxsatingiz mavjud emas."


class CanRejectUniversity(BaseUniversityPermission):
    permission_codename = "reject_university"
    message = "Universitetni rad etish uchun ruxsatingiz mavjud emas."


class CanPublishUniversity(BaseUniversityPermission):
    permission_codename = "publish_university"
    message = "Universitetni nashr qilish uchun ruxsatingiz mavjud emas."
