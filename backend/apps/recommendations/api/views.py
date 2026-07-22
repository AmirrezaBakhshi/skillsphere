from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.recommendations.api.serializers import ProjectRecommendationSerializer
from apps.recommendations.application.services import GetRecommendationsForUserService
from apps.recommendations.infrastructure.django.catalog import DjangoProjectCatalog


class ProjectRecommendationsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        service = GetRecommendationsForUserService(catalog=DjangoProjectCatalog())
        recommendations = service.recommend(user_id=request.user.id)
        data = ProjectRecommendationSerializer([r.__dict__ for r in recommendations], many=True).data
        return Response(data)
