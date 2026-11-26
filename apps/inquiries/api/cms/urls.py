
from django.urls import path

from apps.inquiries.api.cms.views.inquiry_views import (
    InquiryListCreateAPIView,
    InquiryDetailAPIView,
    InquiryStatusUpdateAPIView,
    InquiryAssignmentAPIView,
    InquiryActivityListAPIView,
    InquiryCommentCreateAPIView,
)


urlpatterns = [
    path("inquiries/", InquiryListCreateAPIView.as_view(), name="admin-inquiry-list", ),
    path("inquiries/<uuid:pk>/", InquiryDetailAPIView.as_view(), name="admin-inquiry-detail",),
    path("inquiries/<uuid:pk>/status/", InquiryStatusUpdateAPIView.as_view(), name="admin-inquiry-status-update", ),
    path("inquiries/<uuid:pk>/assign/", InquiryAssignmentAPIView.as_view(), name="admin-inquiry-assign",),
    path("inquiries/<uuid:pk>/activities/", InquiryActivityListAPIView.as_view(), name="admin-inquiry-activity-list",),
    path("inquiries/<uuid:pk>/comments/", InquiryCommentCreateAPIView.as_view(), name="admin-inquiry-comment-create",),

]
