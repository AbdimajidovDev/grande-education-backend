from django.urls import path

from apps.education_content.api.views.public import (
    PublicHybridTeacherListView,
    PublicLearningComponentListView,
    PublicUniversityStepPageView,
)


urlpatterns = [
    path("hybrid-teachers/", PublicHybridTeacherListView.as_view(), name="public-hybrid-teachers", ),
    path("learning-components/", PublicLearningComponentListView.as_view(), name="public-learning-components",),
    path("university-step-page/", PublicUniversityStepPageView.as_view(), name="public-university-step-page", ),
]