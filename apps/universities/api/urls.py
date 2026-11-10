from django.urls import path, include


urlpatterns = [
    # Public API
    path("public/", include("apps.universities.api.public.urls")),

    # CMS API
    path("admin/", include("apps.universities.api.cms.urls")),
]