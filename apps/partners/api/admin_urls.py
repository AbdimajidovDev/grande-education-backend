from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.partners.api.views import PartnerViewSet


router = DefaultRouter()
router.register("partners", PartnerViewSet, basename="admin-partners",)

urlpatterns = [
    path("", include(router.urls)),
]
