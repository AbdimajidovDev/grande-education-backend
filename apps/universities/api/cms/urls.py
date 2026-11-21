
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
from apps.universities.api.cms.views.translation_views import (
    UniversityTranslationListCreateAPIView,
    UniversityTranslationRevisionListCreateAPIView,
    UniversityTranslationRevisionDetailAPIView,
    UniversityTranslationRevisionSubmitAPIView,
    UniversityTranslationRevisionApproveAPIView,
    UniversityTranslationRevisionRejectAPIView,
    UniversityTranslationRevisionPublishAPIView,
)
from apps.universities.api.cms.views.admission_period_views import (
    UniversityAdmissionPeriodListCreateAPIView,
    UniversityAdmissionPeriodDetailAPIView,
)
from apps.universities.api.cms.views.major_views import (
    UniversityMajorListCreateAPIView,
    UniversityMajorDetailAPIView,
    UniversityMajorTranslationAPIView,
)
from apps.universities.api.cms.views.media_views import (
    UniversityMediaListCreateAPIView,
    UniversityMediaDetailAPIView,
)
from apps.universities.api.cms.views.faq_views import (
    FAQListCreateAPIView,
    FAQDetailAPIView,
    FAQTranslationListCreateAPIView,
    FAQRevisionListCreateAPIView,
    FAQRevisionDetailAPIView,
    FAQRevisionWorkflowAPIView,
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


    # University translations
    path("translations/<uuid:university_id>/", UniversityTranslationListCreateAPIView.as_view(), name="university-translation-list-create",),

    # Translation revisions
    path("translations/<uuid:translation_id>/revisions/", UniversityTranslationRevisionListCreateAPIView.as_view(), name="university-translation-revision-list-create",),
    path("translation-revisions/<uuid:revision_id>/", UniversityTranslationRevisionDetailAPIView.as_view(), name="university-translation-revision-detail",),
    path("translation-revisions/<uuid:revision_id>/submit/", UniversityTranslationRevisionSubmitAPIView.as_view(), name="university-translation-revision-submit",),
    path("translation-revisions/<uuid:revision_id>/approve/", UniversityTranslationRevisionApproveAPIView.as_view(), name="university-translation-revision-approve",),
    path("translation-revisions/<uuid:revision_id>/reject/", UniversityTranslationRevisionRejectAPIView.as_view(), name="university-translation-revision-reject"),
    path("translation-revisions/<uuid:revision_id>/publish/", UniversityTranslationRevisionPublishAPIView.as_view(), name="university-translation-revision-publish",),

    # University admission periods
    path("university-revisions/<uuid:revision_id>/admission-periods/", UniversityAdmissionPeriodListCreateAPIView.as_view(), name="university-admission-period-list-create", ),
    path("admission-periods/<uuid:period_id>/", UniversityAdmissionPeriodDetailAPIView.as_view(), name="university-admission-period-detail", ),

    # University majors
    path("university-revisions/<uuid:revision_id>/majors/", UniversityMajorListCreateAPIView.as_view(), name="university-major-list-create", ),
    path("majors/<uuid:major_id>/", UniversityMajorDetailAPIView.as_view(), name="university-major-detail", ),
    path("majors/<uuid:major_id>/translations/", UniversityMajorTranslationAPIView.as_view(), name="university-major-translation", ),

    # University media
    path("university-revisions/<uuid:revision_id>/media/", UniversityMediaListCreateAPIView.as_view(), name="university-media-list-create", ),
    path("media/<uuid:media_id>/", UniversityMediaDetailAPIView.as_view(), name="university-media-detail", ),

    path("faqs/", FAQListCreateAPIView.as_view(), name="faq-list-create",),
    path( "faqs/<uuid:faq_id>/", FAQDetailAPIView.as_view(), name="faq-detail",),
    path("faqs/<uuid:faq_id>/translations/", FAQTranslationListCreateAPIView.as_view(), name="faq-translation-list-create",),
    path("faq-translations/<uuid:translation_id>/revisions/", FAQRevisionListCreateAPIView.as_view(), name="faq-revision-list-create",),
    path("faq-revisions/<uuid:revision_id>/", FAQRevisionDetailAPIView.as_view(), name="faq-revision-detail",),
    path("faq-revisions/<uuid:revision_id>/<str:action>/", FAQRevisionWorkflowAPIView.as_view(), name="faq-revision-workflow",),
]
