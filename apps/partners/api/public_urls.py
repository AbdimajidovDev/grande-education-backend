from django.urls import path

from apps.partners.api.views import PublicPartnerListView


urlpatterns = [
    path(
        "partners/",
        PublicPartnerListView.as_view(),
        name="public-partner-list",
    ),
]