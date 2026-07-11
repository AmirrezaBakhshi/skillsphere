from django.urls import path

from apps.activity.api.views import MyActivityView

app_name = "activity"

urlpatterns = [
    path("me/", MyActivityView.as_view(), name="my-activity"),
]
