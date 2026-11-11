
from django.urls import path

from apps.universities.api.public.views.university_views import (
    PublicUniversityListAPIView,
    PublicUniversityDetailAPIView,
)
from apps.universities.api.public.views.admission_period_views import (
    PublicUniversityAdmissionPeriodListAPIView,
)
from apps.universities.api.public.views.faq_views import (
    PublicFAQListAPIView,
)



urlpatterns = [
    path("universities/", PublicUniversityListAPIView.as_view(), name="public-university-list", ),
    path("universities/<slug:slug>/", PublicUniversityDetailAPIView.as_view(), name="public-university-detail",),
    path("universities/<slug:slug>/admission-periods/", PublicUniversityAdmissionPeriodListAPIView.as_view(), name="public-university-admission-period-list",),

    path("faqs/", PublicFAQListAPIView.as_view(), name="public-faq-list",),
]
