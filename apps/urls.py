from django.urls import path, include


urlpatterns = [
    # Admin API
    path("admin/", include("apps.rbac.api.urls")),
    path("admin/", include("apps.users.api.urls")),

    # Public API
    # path("public/", include("apps.universities.api.urls")),
    # path("public/", include("apps.programs.api.urls")),
]