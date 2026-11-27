
from rest_framework.permissions import BasePermission

from apps.rbac.services.role_service import RoleService


def _has_inquiry_permission(user, permission: str) -> bool:
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


class CanViewInquiries(BasePermission):
    message = "Arizalarni ko'rish uchun ruxsatingiz mavjud emas."

    def has_permission(self, request, view):
        return _has_inquiry_permission(
            request.user,
            "inquiries.view_inquiry",
        )


class CanViewAllInquiries(BasePermission):
    message = "Barcha arizalarni ko'rish uchun ruxsatingiz mavjud emas."

    def has_permission(self, request, view):
        return _has_inquiry_permission(
            request.user,
            "inquiries.view_all_inquiries",
        )


class CanAddInquiry(BasePermission):
    message = "Ariza yaratish uchun ruxsatingiz mavjud emas."

    def has_permission(self, request, view):
        return _has_inquiry_permission(
            request.user,
            "inquiries.add_inquiry",
        )


class CanChangeInquiry(BasePermission):
    message = "Arizani o'zgartirish uchun ruxsatingiz mavjud emas."

    def has_permission(self, request, view):
        return _has_inquiry_permission(
            request.user,
            "inquiries.change_inquiry",
        )


class CanChangeInquiryStatus(BasePermission):
    message = "Ariza holatini o'zgartirish uchun ruxsatingiz mavjud emas."

    def has_permission(self, request, view):
        return _has_inquiry_permission(
            request.user,
            "inquiries.change_inquiry_status",
        )


class CanAssignInquiry(BasePermission):
    message = "Arizani xodimga biriktirish uchun ruxsatingiz mavjud emas."

    def has_permission(self, request, view):
        return _has_inquiry_permission(
            request.user,
            "inquiries.assign_inquiry",
        )


class CanViewInquiryActivity(BasePermission):
    message = "Ariza tarixini ko'rish uchun ruxsatingiz mavjud emas."

    def has_permission(self, request, view):
        return _has_inquiry_permission(
            request.user,
            "inquiries.view_inquiry_activity",
        )


class CanDeleteInquiry(BasePermission):
    message = "Arizani o'chirish uchun ruxsatingiz mavjud emas."

    def has_permission(self, request, view):
        return _has_inquiry_permission(
            request.user,
            "inquiries.delete_inquiry",
        )
