from django.urls import path

from apps.recommendations.api.views import ProjectRecommendationsView

app_name = "recommendations"

urlpatterns = [
    path("projects/", ProjectRecommendationsView.as_view(), name="projects"),
]
