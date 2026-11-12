
from django.urls import path

from apps.inquiries.api.public.views.category_views import (
    PublicInquiryCategoryListAPIView,
)
from apps.inquiries.api.public.views.inquiry_views import (
    PublicInquiryCreateAPIView,
)


urlpatterns = [
    path("inquiry-categories/", PublicInquiryCategoryListAPIView.as_view(), name="public-inquiry-category-list",),
    path("inquiries/", PublicInquiryCreateAPIView.as_view(), name="public-inquiry-create", ),
]
