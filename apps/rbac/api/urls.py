from django.urls import path

from apps.rbac.api.views import (
    RoleListCreateAPIView,
    RoleDetailAPIView,
    RolePermissionAPIView,
    PermissionListAPIView,
    RoleUserAPIView,
)

urlpatterns = [
    # Roles
    path("roles/", RoleListCreateAPIView.as_view(), name="role-list-create", ),
    path("roles/<int:role_id>/", RoleDetailAPIView.as_view(), name="role-detail", ),

    # Role permissions
    path("roles/permissions/", PermissionListAPIView.as_view(), name="permission-list",),
    path("roles/<int:role_id>/permissions/", RolePermissionAPIView.as_view(), name="role-permissions",),

    path("roles/<int:role_id>/users/", RoleUserAPIView.as_view(), name="role-users",),
]