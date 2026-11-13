
from django.urls import path

from apps.site_settings.api.views.public import (
    PublicSiteStatListView,
    PublicContactView,
)

app_name = "site-settings-public"

urlpatterns = [
    path(
        "site-stats/",
        PublicSiteStatListView.as_view(),
        name="public-site-stats",
    ),
    path(
        "contacts/",
        PublicContactView.as_view(),
        name="public-contacts",
    ),
]
