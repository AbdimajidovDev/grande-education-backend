from rest_framework.permissions import BasePermission


class IsActiveEmployee(BasePermission):
    """Faqat autentifikatsiyadan o'tgan faol CMS xodimi."""

    message = "Bildirishnomalarni ko'rish uchun faol xodim bo'lishingiz kerak."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_active)
