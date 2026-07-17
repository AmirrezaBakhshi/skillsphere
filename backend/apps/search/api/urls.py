from django.urls import path

from apps.search.api.views import ProjectSearchView, UserSearchView

app_name = "search"

urlpatterns = [
    path("projects/", ProjectSearchView.as_view(), name="projects"),
    path("users/", UserSearchView.as_view(), name="users"),
]
