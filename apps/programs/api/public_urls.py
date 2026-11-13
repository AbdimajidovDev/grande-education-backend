from django.urls import path

from apps.programs.api.views import PublicProgramListView

app_name = "programs-public"

urlpatterns = [
    path("programs/", PublicProgramListView.as_view(), name="program-list", ),
]