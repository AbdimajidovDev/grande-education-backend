
from django.urls import path

from apps.teachers.api.views import PublicTeacherListView


urlpatterns = [
    path("teachers/", PublicTeacherListView.as_view(), name="public-teacher-list", ),
]
