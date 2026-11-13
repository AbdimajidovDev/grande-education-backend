from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.programs.api.views import ProgramViewSet

app_name = "programs-admin"

router = DefaultRouter()
router.register("programs", ProgramViewSet, basename="admin-programs",)

urlpatterns = [
    path("", include(router.urls)),
]