from django.urls import path

from apps.admissions.api.views import (
    AdmissionListCreateAPIView,
    AdmissionDetailAPIView,
    AdmissionUpdateAPIView,
)

urlpatterns = [
    path("admissions/", AdmissionListCreateAPIView.as_view(), name="admin-admission-list", ),
    path("admissions/<uuid:pk>/", AdmissionDetailAPIView.as_view(), name="admin-admission-detail", ),
]