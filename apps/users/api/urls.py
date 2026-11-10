from django.urls import path

from apps.users.api.views import (
    EmployeeListCreateAPIView,
    EmployeeDetailAPIView,
    EmployeeActivateAPIView,
    EmployeeRoleAssignmentAPIView,
    EmployeeRoleRemovalAPIView,
)


urlpatterns = [
    path("employees/", EmployeeListCreateAPIView.as_view(), name="employee-list-create",),
    path("employees/<int:pk>/", EmployeeDetailAPIView.as_view(), name="employee-detail",),
    path("employees/<int:pk>/activate/", EmployeeActivateAPIView.as_view(), name="employee-activate",),
    path("employees/<int:pk>/roles/", EmployeeRoleAssignmentAPIView.as_view(), name="employee-role-assignment",),
    path("employees/<int:pk>/roles/remove/", EmployeeRoleRemovalAPIView.as_view(), name="employee-role-removal",),
]
