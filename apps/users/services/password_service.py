from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()


class PasswordService:
    """Foydalanuvchi parollarini boshqarish xizmatlari."""

    @staticmethod
    @transaction.atomic
    def change_password(*, user: User, new_password: str) -> None:
        """
        Foydalanuvchi parolini yangilaydi.

        Mavjud autentifikatsiya sessiyalarini bekor qilmaydi.
        """

        user.set_password(new_password)
        user.save(update_fields=["password"])