from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.search.api.serializers import ProjectSearchResultSerializer, UserSearchResultSerializer
from apps.search.application.services import SearchProjectsService, SearchUsersService
from apps.search.domain.exceptions import SearchUnavailableError
from apps.search.infrastructure.elasticsearch.adapters import (
    ElasticsearchProjectSearch,
    ElasticsearchUserSearch,
)

# Search is intentionally public (AllowAny) - browsing what others have
# built doesn't require an account, matching the "explore others' work"
# goal from the project brief. Downloading still requires auth.


class ProjectSearchView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        query = request.query_params.get("q", "")
        service = SearchProjectsService(repository=ElasticsearchProjectSearch())
        try:
            results = service.search(query)
        except SearchUnavailableError:
            return Response({"detail": "Search is temporarily unavailable"}, status=503)
        return Response(ProjectSearchResultSerializer([r.__dict__ for r in results], many=True).data)


class UserSearchView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        query = request.query_params.get("q", "")
        service = SearchUsersService(repository=ElasticsearchUserSearch())
        try:
            results = service.search(query)
        except SearchUnavailableError:
            return Response({"detail": "Search is temporarily unavailable"}, status=503)
        return Response(UserSearchResultSerializer([r.__dict__ for r in results], many=True).data)
