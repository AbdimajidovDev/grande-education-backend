from django.db import models

# Create your models here.

from django.contrib.auth.models import Group


class Role(Group):
    """
    Proxy model for managing custom RBAC permissions.

    Uses Django's built-in auth.Group table.
    No additional database table is created.
    """

    class Meta:
        proxy = True
        app_label = "rbac"
        verbose_name = "Role"
        verbose_name_plural = "Roles"
        permissions = [
            ("manage_roles", "Can manage roles"),
        ]
