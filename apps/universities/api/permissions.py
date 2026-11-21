
from rest_framework.permissions import BasePermission

from apps.rbac.services.role_service import RoleService


class BaseUniversityPermission(BasePermission):
    permission_codename = None
    fallback_codenames = ()

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated or not user.is_active:
            return False

        if user.is_superuser:
            return True

        if not self.permission_codename:
            return False

        user_permissions = RoleService._get_actor_role_permissions(user)

        required_permissions = [f"universities.{self.permission_codename}"]
        for fallback in self.fallback_codenames:
            required_permissions.append(f"universities.{fallback}")

        return any(perm in user_permissions for perm in required_permissions)


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


# Major permissions
class CanViewUniversityMajors(BaseUniversityPermission):
    permission_codename = "view_universitymajor"
    fallback_codenames = ("view_university", "change_university")
    message = "Universitet yo'nalishlarini ko'rish uchun ruxsatingiz mavjud emas."


class CanCreateUniversityMajor(BaseUniversityPermission):
    permission_codename = "add_universitymajor"
    fallback_codenames = ("change_university",)
    message = "Universitet yo'nalishi qo'shish uchun ruxsatingiz mavjud emas."


class CanUpdateUniversityMajor(BaseUniversityPermission):
    permission_codename = "change_universitymajor"
    fallback_codenames = ("change_university",)
    message = "Universitet yo'nalishini tahrirlash uchun ruxsatingiz mavjud emas."


class CanDeleteUniversityMajor(BaseUniversityPermission):
    permission_codename = "delete_universitymajor"
    fallback_codenames = ("change_university",)
    message = "Universitet yo'nalishini o'chirish uchun ruxsatingiz mavjud emas."


# Media permissions
class CanViewUniversityMedia(BaseUniversityPermission):
    permission_codename = "view_universitymedia"
    fallback_codenames = ("view_university", "change_university")
    message = "Universitet media fayllarini ko'rish uchun ruxsatingiz mavjud emas."


class CanCreateUniversityMedia(BaseUniversityPermission):
    permission_codename = "add_universitymedia"
    fallback_codenames = ("change_university",)
    message = "Universitet media fayli qo'shish uchun ruxsatingiz mavjud emas."


class CanUpdateUniversityMedia(BaseUniversityPermission):
    permission_codename = "change_universitymedia"
    fallback_codenames = ("change_university",)
    message = "Universitet media faylini tahrirlash uchun ruxsatingiz mavjud emas."


class CanDeleteUniversityMedia(BaseUniversityPermission):
    permission_codename = "delete_universitymedia"
    fallback_codenames = ("change_university",)
    message = "Universitet media faylini o'chirish uchun ruxsatingiz mavjud emas."
