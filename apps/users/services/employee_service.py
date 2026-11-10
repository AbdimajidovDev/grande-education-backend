
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from apps.users.services.exceptions import EmployeeNotFoundError
from apps.rbac.services.role_service import RoleService

User = get_user_model()


class EmployeeService:
    """CMS xodimlarini boshqarish xizmatlari."""

    @staticmethod
    def _ensure_permission(actor: User, permission: str) -> None:
        if (
                actor is None
                or not actor.is_authenticated
                or not actor.is_active
        ):
            raise PermissionDenied(
                "Ushbu amalni bajarish uchun faol foydalanuvchi bo'lishingiz kerak."
            )

        if actor.is_superuser:
            return

        actor_permissions = RoleService._get_actor_role_permissions(actor)

        if f"users.{permission}" not in actor_permissions:
            raise PermissionDenied(
                "Ushbu amalni bajarish uchun ruxsatingiz mavjud emas."
            )


    @staticmethod
    def _ensure_managed_employee(employee: User) -> None:
        if employee.is_superuser or employee.is_staff:
            raise PermissionDenied(
                "Django Admin hisoblarini CMS API orqali boshqarish mumkin emas."
            )

    @staticmethod
    def _is_username_unique_violation(exc: IntegrityError) -> bool:
        cause = exc.__cause__ or exc

        constraint_name = getattr(
            getattr(cause, "diag", None),
            "constraint_name",
            None,
        )

        if constraint_name == "unique_user_username_ci":
            return True

        return "unique_user_username_ci" in str(cause)

    @staticmethod
    def _raise_username_conflict(exc: IntegrityError) -> None:
        if EmployeeService._is_username_unique_violation(exc):
            raise ValidationError({
                "username": "Ushbu username band."
            }) from exc

        raise exc

    @staticmethod
    @transaction.atomic
    def create_employee(
            actor,
            username,
            password,
            first_name="",
            last_name="",
            email="",
            phone_number="",
            role_ids: list[int] | None = None,
    ):
        """Yangi CMS xodimini yaratadi va ixtiyoriy rollarni biriktiradi."""

        # 1. Xodim yaratish vakolatini tekshirish.
        EmployeeService._ensure_permission(
            actor,
            "add_user",
        )

        # 2. Rollar ro'yxatini normallashtirish.
        role_ids = role_ids or []

        # 3. Rol biriktirish vakolatini tekshirish.
        if role_ids:
            EmployeeService._ensure_permission(
                actor,
                "assign_roles",
            )

        # 4. Takroriy role ID larni tekshirish.
        if len(role_ids) != len(set(role_ids)):
            raise ValidationError({
                "role_ids": "Rol ID raqamlari takrorlanmasligi kerak."
            })

        # 5. Ma'lumotlarni tozalash.
        username = username.strip()
        first_name = first_name.strip()
        last_name = last_name.strip()
        email = email.strip()
        phone_number = phone_number.strip()

        if not username:
            raise ValidationError({
                "username": "Username kiritilishi shart."
            })

        if not password:
            raise ValidationError({
                "password": "Parol kiritilishi shart."
            })

        # 6. Username takrorlanishini tekshirish.
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError({
                "username": "Ushbu username band."
            })

        # 7. Xodim obyektini yaratish.
        employee = User(
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone_number=phone_number,
            is_active=True,
            is_staff=False,
            is_superuser=False,
        )

        validate_password(password, user=employee)
        employee.set_password(password)

        # 8. Xodimni saqlash va rollarni biriktirish.
        try:
            employee.save()

            if role_ids:
                RoleService.assign_employee_to_roles(
                    role_ids=role_ids,
                    employee=employee,
                    actor=actor,
                )

        except IntegrityError as exc:
            EmployeeService._raise_username_conflict(exc)

        return employee


    @staticmethod
    @transaction.atomic
    def update_employee(
        *,
        actor: User,
        employee_id,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        email: str | None = None,
        phone_number: str | None = None,
    ) -> User:
        """Xodimning profil ma'lumotlarini yangilaydi."""

        EmployeeService._ensure_permission(
            actor,
            "change_user",
        )

        employee = (
            User.objects
            .select_for_update()
            .filter(pk=employee_id)
            .first()
        )

        if employee is None:
            raise EmployeeNotFoundError("Xodim topilmadi.")

        EmployeeService._ensure_managed_employee(employee)

        update_fields = []

        if username is not None:
            username = username.strip()

            if not username:
                raise ValidationError({
                    "username": "Username bo'sh bo'lishi mumkin emas."
                })

            username_exists = (
                User.objects
                .filter(username__iexact=username)
                .exclude(pk=employee.pk)
                .exists()
            )

            if username_exists:
                raise ValidationError({
                    "username": "Ushbu username band."
                })

            employee.username = username
            update_fields.append("username")

        if first_name is not None:
            employee.first_name = first_name.strip()
            update_fields.append("first_name")

        if last_name is not None:
            employee.last_name = last_name.strip()
            update_fields.append("last_name")

        if email is not None:
            employee.email = email.strip()
            update_fields.append("email")

        if phone_number is not None:
            employee.phone_number = phone_number.strip()
            update_fields.append("phone_number")

        if not update_fields:
            raise ValidationError(
                "Yangilash uchun kamida bitta maydon yuborilishi kerak."
            )

        try:
            with transaction.atomic():
                employee.save(update_fields=update_fields)
        except IntegrityError as exc:
            EmployeeService._raise_username_conflict(exc)
        return employee


    @staticmethod
    @transaction.atomic
    def deactivate_employee(
        *,
        actor: User,
        employee_id,
    ) -> User:
        """Xodim hisobini deaktivatsiya qiladi."""

        EmployeeService._ensure_permission(
            actor,
            "change_user",
        )

        employee = (
            User.objects
            .select_for_update()
            .filter(pk=employee_id)
            .first()
        )

        if employee is None:
            raise EmployeeNotFoundError("Xodim topilmadi.")

        if employee.pk == actor.pk:
            raise ValidationError(
                "O'zingizning hisobingizni deaktivatsiya qila olmaysiz."
            )

        EmployeeService._ensure_managed_employee(employee)

        if not employee.is_active:
            raise ValidationError(
                "Xodim allaqachon deaktivatsiya qilingan."
            )

        employee.is_active = False
        employee.save(update_fields=["is_active"])

        return employee


    @staticmethod
    @transaction.atomic
    def activate_employee(
        *,
        actor: User,
        employee_id,
    ) -> User:
        """Deaktivatsiya qilingan xodim hisobini faollashtiradi."""

        EmployeeService._ensure_permission(
            actor,
            "change_user",
        )

        employee = (
            User.objects
            .select_for_update()
            .filter(pk=employee_id)
            .first()
        )

        if employee is None:
            raise EmployeeNotFoundError("Xodim topilmadi.")

        EmployeeService._ensure_managed_employee(employee)

        if employee.is_active:
            raise ValidationError(
                "Xodim allaqachon faol holatda."
            )

        employee.is_active = True
        employee.save(update_fields=["is_active"])

        return employee


