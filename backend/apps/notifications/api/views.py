from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.api.serializers import NotificationSerializer
from apps.notifications.application.services import (
    ListNotificationsService,
    MarkNotificationReadService,
)
from apps.notifications.infrastructure.django.repositories import DjangoNotificationRepository

_repository = DjangoNotificationRepository()


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        unread_only = request.query_params.get("unread") == "true"
        service = ListNotificationsService(repository=_repository)
        entries = service.list_for_user(request.user.id, unread_only=unread_only)
        data = NotificationSerializer([e.__dict__ for e in entries], many=True).data
        return Response(data)


class NotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, notification_id: int):
        service = MarkNotificationReadService(repository=_repository)
        entity = service.mark_read(notification_id=notification_id, user_id=request.user.id)
        return Response(NotificationSerializer(entity.__dict__).data)
