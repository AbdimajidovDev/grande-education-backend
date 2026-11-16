from django.db import models


class DashboardAccess(models.Model):
    """
    Defines permissions for dashboard access.
    No database table is created for this model.
    """

    class Meta:
        managed = False
        default_permissions = ()
        permissions = [
            ("view_dashboard", "Can view dashboard"),
        ]