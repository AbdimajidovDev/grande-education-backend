from django.urls import path

from apps.directions.api.views import DirectionPublicListView

urlpatterns = [
    path(
        "directions/",
        DirectionPublicListView.as_view(),
        name="public-directions",
    ),
]