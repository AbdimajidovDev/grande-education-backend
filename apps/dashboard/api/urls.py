from django.urls import path

from apps.dashboard.api.views.overview import (
    DashboardOverviewAPIView,
)

app_name = "dashboard"

urlpatterns = [
    path("overview/",DashboardOverviewAPIView.as_view(), name="overview",),
]
