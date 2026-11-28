from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import override_settings

User = get_user_model()

# Testlarda real Redis o'rniga jarayon ichidagi layer (production'da emas).
IN_MEMORY_CHANNEL_LAYERS = {
    "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
}

ALLOWED_ORIGIN = "http://localhost:5173"

notification_test_settings = override_settings(
    CHANNEL_LAYERS=IN_MEMORY_CHANNEL_LAYERS,
    WEBSOCKET_ALLOWED_ORIGINS=[ALLOWED_ORIGIN],
)


def make_user(username: str, *permissions: str, is_active: bool = True, **extra):
    """`app_label.codename` ko'rinishidagi permissionlarni rol orqali beradi."""

    user = User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="Password123!",
        is_active=is_active,
        **extra,
    )

    if permissions:
        group = Group.objects.create(name=f"Role_{username}")
        for permission in permissions:
            app_label, codename = permission.split(".", 1)
            group.permissions.add(
                Permission.objects.get(
                    content_type__app_label=app_label,
                    codename=codename,
                )
            )
        user.groups.add(group)

    return user


def make_superuser(username: str):
    return User.objects.create_superuser(
        username=username,
        email=f"{username}@example.com",
        password="Password123!",
    )
