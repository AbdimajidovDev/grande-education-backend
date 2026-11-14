from rest_framework.routers import DefaultRouter

from apps.education_content.api.views.admin import (
    HybridTeacherViewSet,
    LearningComponentViewSet,
    UniversityStepPageViewSet,
    UniversityStepViewSet,
)


router = DefaultRouter()

router.register("hybrid-teachers", HybridTeacherViewSet, basename="admin-hybrid-teachers",)

router.register("learning-components", LearningComponentViewSet, basename="admin-learning-components",)

router.register("university-step-pages", UniversityStepPageViewSet, basename="admin-university-step-pages" )

router.register("university-steps", UniversityStepViewSet, basename="admin-university-steps",)

urlpatterns = router.urls