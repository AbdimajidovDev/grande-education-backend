from django.contrib.auth import get_user_model
from django.db.models import Q


User = get_user_model()


class EmployeeSelector:
    """CMS xodimlarini database'dan olish uchun selectorlar."""

    @staticmethod
    def get_employee_queryset(
        *,
        search: str | None = None,
        is_active: bool | None = None,
    ):
        """CMS xodimlari ro'yxati uchun QuerySet qaytaradi."""


        queryset = (
            User.objects.filter(is_staff=False, is_superuser=False,).prefetch_related("groups")
        )

        if search:
            search = search.strip()

            if search:
                queryset = queryset.filter(
                    Q(username__icontains=search)
                    | Q(first_name__icontains=search)
                    | Q(last_name__icontains=search)
                    | Q(email__icontains=search)
                    | Q(phone_number__icontains=search)
                )

        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)

        return queryset.order_by("-date_joined")



    @staticmethod
    def get_employee_by_id(*, employee_id):
        """ID orqali CMS xodimini topadi."""
        return (
            User.objects
            .filter(
                pk=employee_id,
                is_staff=False,
                is_superuser=False,
            )
            .prefetch_related("groups")
            .first()
        )