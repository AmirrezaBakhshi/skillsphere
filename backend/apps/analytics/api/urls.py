from django.urls import path

from apps.analytics.api.views import AdminDashboardView, UserDashboardView

app_name = "analytics"

urlpatterns = [
    path("me/", UserDashboardView.as_view(), name="me"),
    path("admin/", AdminDashboardView.as_view(), name="admin"),
]
