
from django.urls import path

from apps.universities.api.cms.views.university_views import (
    UniversityListCreateAPIView,
    UniversityDetailAPIView,
)

from apps.universities.api.cms.views.revision_views import (
    UniversityRevisionListCreateAPIView,
    UniversityRevisionDetailAPIView,
    UniversityRevisionSubmitAPIView,
    UniversityRevisionApproveAPIView,
    UniversityRevisionRejectAPIView,
    UniversityRevisionPublishAPIView,
)


urlpatterns = [
    # Universities
    path("universities/", UniversityListCreateAPIView.as_view(), name="university-list-create", ),
    path("universities/<uuid:university_id>/", UniversityDetailAPIView.as_view(), name="university-detail", ),

    # University revisions
    path("universities/<uuid:university_id>/revisions/", UniversityRevisionListCreateAPIView.as_view(), name="university-revision-list-create", ),
    path("university-revisions/<uuid:revision_id>/", UniversityRevisionDetailAPIView.as_view(), name="university-revision-detail",),
    path("university-revisions/<uuid:revision_id>/submit/", UniversityRevisionSubmitAPIView.as_view(), name="university-revision-submit",),
    path("university-revisions/<uuid:revision_id>/approve/", UniversityRevisionApproveAPIView.as_view(), name="university-revision-approve",),
    path("university-revisions/<uuid:revision_id>/reject/", UniversityRevisionRejectAPIView.as_view(), name="university-revision-reject",),
    path("university-revisions/<uuid:revision_id>/publish/", UniversityRevisionPublishAPIView.as_view(), name="university-revision-publish",),
]
