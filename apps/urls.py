from django.urls import path, include


urlpatterns = [
    # Admin API
    path("admin/", include("apps.rbac.api.urls")),
    path("admin/", include("apps.users.api.urls")),
    path("admin/", include("apps.programs.api.admin_urls")),
    path("admin/", include("apps.partners.api.admin_urls")),
    path("admin/", include("apps.teachers.api.admin_urls")),


    # Public API
    path("", include("apps.universities.api.urls")),
    path("", include("apps.inquiries.api.urls")),
    path("public/", include("apps.programs.api.public_urls")),
    path("public/", include("apps.partners.api.public_urls")),
    path("public/", include("apps.teachers.api.public_urls")),
]