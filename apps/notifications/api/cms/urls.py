from django.urls import path

from apps.notifications.api.cms.views import (
    NotificationListAPIView,
    NotificationMarkAllReadAPIView,
    NotificationMarkReadAPIView,
    NotificationUnreadCountAPIView,
)


urlpatterns = [
    path("notifications/", NotificationListAPIView.as_view(), name="admin-notification-list",),
    path("notifications/unread-count/", NotificationUnreadCountAPIView.as_view(), name="admin-notification-unread-count",),
    path("notifications/read-all/", NotificationMarkAllReadAPIView.as_view(), name="admin-notification-read-all",),
    path("notifications/<uuid:notification_id>/read/", NotificationMarkReadAPIView.as_view(), name="admin-notification-read",),
]
