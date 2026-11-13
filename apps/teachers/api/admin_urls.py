
from rest_framework.routers import DefaultRouter

from apps.teachers.api.views import TeacherViewSet


router = DefaultRouter()
router.register("teachers", TeacherViewSet, basename="admin-teachers",)

urlpatterns = router.urls
