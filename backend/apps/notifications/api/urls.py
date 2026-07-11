from django.urls import path

from apps.notifications.api.views import NotificationListView, NotificationMarkReadView

app_name = "notifications"

urlpatterns = [
    path("", NotificationListView.as_view(), name="list"),
    path("<int:notification_id>/read/", NotificationMarkReadView.as_view(), name="mark-read"),
]
