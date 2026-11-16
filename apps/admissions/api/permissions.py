
from rest_framework.permissions import BasePermission

from apps.rbac.services.role_service import RoleService


def _has_admission_permission(user, permission: str) -> bool:
    """
    Foydalanuvchining Admission bo'yicha vakolatini tekshiradi.
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


class CanViewAdmissions(BasePermission):
    message = "Admissionlarni ko'rish uchun ruxsatingiz mavjud emas."

    def has_permission(self, request, view):
        return _has_admission_permission(
            request.user,
            "admissions.view_admission",
        )


class CanViewAllAdmissions(BasePermission):
    message = "Barcha Admissionlarni ko'rish uchun ruxsatingiz mavjud emas."

    def has_permission(self, request, view):
        return _has_admission_permission(
            request.user,
            "admissions.view_all_admissions",
        )


class CanAddAdmission(BasePermission):
    message = "Admission yaratish uchun ruxsatingiz mavjud emas."

    def has_permission(self, request, view):
        return _has_admission_permission(
            request.user,
            "admissions.add_admission",
        )


class CanChangeAdmission(BasePermission):
    message = "Admission ma'lumotlarini o'zgartirish uchun ruxsatingiz mavjud emas."

    def has_permission(self, request, view):
        return _has_admission_permission(
            request.user,
            "admissions.change_admission",
        )


class CanChangeAdmissionStage(BasePermission):
    message = "Admission bosqichini o'zgartirish uchun ruxsatingiz mavjud emas."

    def has_permission(self, request, view):
        return _has_admission_permission(
            request.user,
            "admissions.change_admission_stage",
        )


class CanAssignAdmissionCurator(BasePermission):
    message = "Admissionga kurator biriktirish uchun ruxsatingiz mavjud emas."

    def has_permission(self, request, view):
        return _has_admission_permission(
            request.user,
            "admissions.assign_admission_curator",
        )


class CanCancelAdmission(BasePermission):
    message = "Admissionni bekor qilish uchun ruxsatingiz mavjud emas."

    def has_permission(self, request, view):
        return _has_admission_permission(
            request.user,
            "admissions.cancel_admission",
        )


class CanRestoreAdmission(BasePermission):
    message = "Admissionni tiklash uchun ruxsatingiz mavjud emas."

    def has_permission(self, request, view):
        return _has_admission_permission(
            request.user,
            "admissions.restore_admission",
        )


class CanViewAdmissionActivity(BasePermission):
    message = "Admission faoliyati tarixini ko'rish uchun ruxsatingiz mavjud emas."

    def has_permission(self, request, view):
        return _has_admission_permission(
            request.user,
            "admissions.view_admission_activity",
        )


class CanAddAdmissionComment(BasePermission):
    message = "Admissionga izoh qo'shish uchun ruxsatingiz mavjud emas."

    def has_permission(self, request, view):
        return _has_admission_permission(
            request.user,
            "admissions.add_admission_comment",
        )


