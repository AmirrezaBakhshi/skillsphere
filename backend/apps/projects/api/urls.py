from django.urls import path

from apps.projects.api.views import MyProjectsView, ProjectDownloadView, ProjectUploadView

app_name = "projects"

urlpatterns = [
    path("upload/", ProjectUploadView.as_view(), name="upload"),
    path("mine/", MyProjectsView.as_view(), name="mine"),
    path("<uuid:project_id>/download/", ProjectDownloadView.as_view(), name="download"),
]
