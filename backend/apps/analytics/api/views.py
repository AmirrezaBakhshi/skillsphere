from dataclasses import asdict

from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.api.serializers import AdminDashboardSerializer, UserDashboardSerializer
from apps.analytics.application.services import (
    BuildAdminDashboardService,
    BuildUserDashboardService,
)
from apps.analytics.infrastructure.django.queries import DjangoAnalyticsQueries

_repository = DjangoAnalyticsQueries()


class UserDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        service = BuildUserDashboardService(repository=_repository)
        stats = service.build(request.user.id)
        return Response(UserDashboardSerializer(asdict(stats)).data)


class AdminDashboardView(APIView):
    # IsAdminUser checks request.user.is_staff - only Django admin/staff
    # accounts can see system-wide stats.
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        service = BuildAdminDashboardService(repository=_repository)
        stats = service.build()
        return Response(AdminDashboardSerializer(asdict(stats)).data)
