
from django.urls import path, include


urlpatterns = [
    path("public/", include("apps.inquiries.api.public.urls")),
    path("admin/", include("apps.inquiries.api.cms.urls")),
]
