"""Bildirishnoma qabul qiluvchilarini mavjud RBAC qoidalari bo'yicha aniqlash.

Loyihadagi "dynamic RBAC" kabi faqat rollar (Group) orqali berilgan
permissionlar hisobga olinadi (RoleService._get_actor_role_permissions bilan
bir xil semantika). Superuser hamma narsani ko'ra oladi. Nofaol
foydalanuvchilar hech qachon qabul qiluvchi bo'lmaydi.
"""

from collections.abc import Iterable

from django.contrib.auth import get_user_model
from django.db.models import Q, QuerySet

from apps.rbac.services.role_service import RoleService

User = get_user_model()


# Obyektni ko'rish huquqini beradigan permissionlar. Ular tegishli API
# permission klasslari bilan aynan bir xil (o'zgarsa, shu yerda ham
# yangilanishi kerak).
INQUIRY_VIEW_PERMISSIONS = (
    "inquiries.view_inquiry",
    "inquiries.view_all_inquiries",
)
INQUIRY_VIEW_ALL_PERMISSION = "inquiries.view_all_inquiries"

ADMISSION_VIEW_PERMISSIONS = (
    "admissions.view_admission",
    "admissions.view_all_admissions",
)
ADMISSION_VIEW_ALL_PERMISSION = "admissions.view_all_admissions"

UNIVERSITY_VIEW_PERMISSIONS = ("universities.view_university",)
UNIVERSITY_TRANSLATION_VIEW_PERMISSIONS = (
    "universities.view_universitytranslation",
    "universities.view_university",
)
FAQ_VIEW_PERMISSIONS = (
    "universities.view_faq",
    "universities.change_faq",
    "universities.add_faq",
    "universities.submit_review_faq",
    "universities.approve_faq",
    "universities.reject_faq",
    "universities.publish_faq",
    "universities.view_university",
)


def _role_permission_q(permissions: Iterable[str]) -> Q:
    """`app_label.codename` ro'yxati uchun Group permission sharti."""

    condition = Q(pk__in=[])
    for permission in permissions:
        app_label, codename = permission.split(".", 1)
        condition |= Q(
            groups__permissions__content_type__app_label=app_label,
            groups__permissions__codename=codename,
        )
    return condition


def _users_with_any_role_permission(permissions: Iterable[str]) -> QuerySet:
    return (
        User.objects
        .filter(_role_permission_q(permissions))
        .values("pk")
    )


def get_active_users_with_permissions(
    *,
    required: str,
    any_of: Iterable[str] = (),
) -> QuerySet:
    """`required` va (berilgan bo'lsa) `any_of` dan kamida bittasiga ega
    faol foydalanuvchilar + faol superuserlar.
    """

    role_condition = Q(pk__in=_users_with_any_role_permission([required]))

    any_of = tuple(any_of)
    if any_of:
        role_condition &= Q(pk__in=_users_with_any_role_permission(any_of))

    return (
        User.objects
        .filter(is_active=True)
        .filter(Q(is_superuser=True) | role_condition)
        .order_by("pk")
    )


def user_has_any_permission(user, permissions: Iterable[str]) -> bool:
    """Bitta foydalanuvchi uchun RoleService semantikasida tekshiruv."""

    if user is None or not user.is_active:
        return False

    if user.is_superuser:
        return True

    user_permissions = RoleService._get_actor_role_permissions(user)
    return any(permission in user_permissions for permission in permissions)


def can_view_inquiry(user, *, assignee_id: int | None) -> bool:
    """Inquiry ko'rish scope'i: view_all yoki (view + o'ziga biriktirilgan)."""

    if user is None or not user.is_active:
        return False

    if user.is_superuser:
        return True

    user_permissions = RoleService._get_actor_role_permissions(user)

    if INQUIRY_VIEW_ALL_PERMISSION in user_permissions:
        return True

    return (
        "inquiries.view_inquiry" in user_permissions
        and assignee_id == user.pk
    )


def can_view_admission(user, *, curator_id: int | None) -> bool:
    """Admission ko'rish scope'i: view_all yoki (view + o'zi kurator)."""

    if user is None or not user.is_active:
        return False

    if user.is_superuser:
        return True

    user_permissions = RoleService._get_actor_role_permissions(user)

    if ADMISSION_VIEW_ALL_PERMISSION in user_permissions:
        return True

    return (
        "admissions.view_admission" in user_permissions
        and curator_id == user.pk
    )
