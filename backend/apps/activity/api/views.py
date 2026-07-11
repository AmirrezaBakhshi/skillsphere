from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.activity.api.serializers import ActivityLogSerializer
from apps.activity.application.services import ListUserActivityService
from apps.activity.infrastructure.django.repositories import DjangoActivityLogRepository


class MyActivityView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        service = ListUserActivityService(repository=DjangoActivityLogRepository())
        entries = service.list_for_user(request.user.id)
        data = ActivityLogSerializer([e.__dict__ for e in entries], many=True).data
        return Response(data)
