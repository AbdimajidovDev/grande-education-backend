
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.site_settings.api.views.admin import (
    SiteStatViewSet,
    OfficeViewSet,
)

app_name = "site-settings-admin"

router = DefaultRouter()
router.register(
    "site-stats",
    SiteStatViewSet,
    basename="admin-site-stats",
)
router.register(
    "offices",
    OfficeViewSet,
    basename="admin-offices",
)

urlpatterns = [
    path("", include(router.urls)),
]
