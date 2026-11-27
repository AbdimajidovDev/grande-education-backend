from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (
            _("Personal info"),
            {"fields": ("first_name", "last_name", "email", "phone_number")},
        ),
        (
            _("Permissions"),
            {"fields": ("is_active", "is_staff", "is_superuser")},
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    filter_horizontal = ()

    def _get_excluded_fields(self, request, obj=None) -> tuple[str, ...]:
        """RBAC orqali boshqariladigan maydonlarni admin formadan yashiradi."""
        excluded = ["groups", "user_permissions"]
        if not request.user.is_superuser:
            excluded.append("is_superuser")
        return tuple(excluded)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        if not request.user.is_superuser:
            queryset = queryset.filter(is_superuser=False)

        return queryset

    def has_change_permission(self, request, obj=None):
        if obj and obj.is_superuser and not request.user.is_superuser:
            return False

        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.is_superuser and not request.user.is_superuser:
            return False

        return super().has_delete_permission(request, obj)

    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets

        excluded = set(self._get_excluded_fields(request, obj))
        filtered_fieldsets = []

        for name, options in super().get_fieldsets(request, obj):
            fields = tuple(
                field
                for field in options.get("fields", ())
                if field not in excluded
            )
            if not fields:
                continue
            filtered_fieldsets.append((name, {**options, "fields": fields}))

        return tuple(filtered_fieldsets)

    def get_form(self, request, obj=None, **kwargs):
        exclude = list(kwargs.get("exclude") or [])
        exclude.extend(self._get_excluded_fields(request, obj))
        kwargs["exclude"] = tuple(dict.fromkeys(exclude))

        return super().get_form(request, obj, **kwargs)


    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            obj.is_superuser = False

        elif change:
            with transaction.atomic():
                if not obj.is_superuser:
                    superuser_ids = list(
                        User.objects.select_for_update()
                        .filter(is_superuser=True)
                        .values_list("id", flat=True)
                    )

                    if obj.pk in superuser_ids and len(superuser_ids) <= 1:
                        raise PermissionDenied(
                            "Oxirgi Super Admin huquqlarini olib tashlab bo‘lmaydi."
                        )

                super().save_model(request, obj, form, change)

            return

        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        if obj.is_superuser and not request.user.is_superuser:
            raise PermissionDenied(
                "Super Admin hisobini o‘chirish uchun ruxsatingiz mavjud emas."
            )

        with transaction.atomic():
            if obj.is_superuser:
                superuser_ids = list(
                    User.objects.select_for_update()
                    .filter(is_superuser=True)
                    .values_list("id", flat=True)
                )

                if obj.pk in superuser_ids and len(superuser_ids) <= 1:
                    raise PermissionDenied(
                        "Oxirgi Super Admin hisobini o‘chirib bo‘lmaydi."
                    )

            super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        if not request.user.is_superuser and queryset.filter(
                is_superuser=True
        ).exists():
            raise PermissionDenied(
                "Super Admin hisobini o‘chirish uchun ruxsatingiz mavjud emas."
            )

        with transaction.atomic():
            deleting_superuser_ids = set(
                queryset.filter(is_superuser=True).values_list("id", flat=True)
            )

            if deleting_superuser_ids:
                current_superuser_ids = list(
                    User.objects.select_for_update()
                    .filter(is_superuser=True)
                    .values_list("id", flat=True)
                )

                if len(current_superuser_ids) - len(deleting_superuser_ids) < 1:
                    raise PermissionDenied(
                        "Oxirgi Super Admin hisobini o‘chirib bo‘lmaydi."
                    )

            super().delete_queryset(request, queryset)

