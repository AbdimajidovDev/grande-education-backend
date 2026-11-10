
from django.contrib.auth.models import Group, Permission
from django.db.models import Count
from django.db.models import Count, F, Q

class RoleSelector:
    """
    Handles read-only role and permission queries.
    """

    @staticmethod
    def get_roles():
        return (
            Group.objects
            .annotate(user_count=Count("user"))
            .order_by("name")
        )

    @staticmethod
    def get_role_by_id(*, role_id: int):
        return (
            Group.objects
            .annotate(user_count=Count("user"))
            .prefetch_related("permissions")
            .filter(pk=role_id)
            .first()
        )

    @staticmethod
    def get_role_permissions(*, role_id: int):
        return (
            Permission.objects
            .filter(group__id=role_id)
            .select_related("content_type")
            .order_by(
                "content_type__app_label",
                "codename",
            )
        )

    @staticmethod
    def get_all_permissions():
        return (
            Permission.objects
            .select_related("content_type")
            .order_by(
                "content_type__app_label",
                "codename",
            )
        )

    @staticmethod
    def get_role_users(
        *,
        role_id: int,
        search: str | None = None,
        is_active: bool | None = None,
    ):
        queryset = Group.objects.filter(
            pk=role_id
        )

        users = queryset.values(
            user_id=F("user__id"),
            username=F("user__username"),
            first_name=F("user__first_name"),
            last_name=F("user__last_name"),
            email=F("user__email"),
            is_active=F("user__is_active"),
        )

        if search:
            users = users.filter(
                Q(user__username__icontains=search)
                | Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
                | Q(user__email__icontains=search)
            )

        if is_active is not None:
            users = users.filter(user__is_active=is_active)

        return users.order_by("user__id")

    @staticmethod
    def role_exists(*, role_id: int) -> bool:
        return Group.objects.filter(pk=role_id).exists()