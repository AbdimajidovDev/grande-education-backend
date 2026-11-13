from rest_framework.routers import DefaultRouter

from apps.directions.api.views import DirectionAdminViewSet

router = DefaultRouter()
router.register(
    "directions",
    DirectionAdminViewSet,
    basename="admin-directions",
)

urlpatterns = router.urls