from dataclasses import asdict

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chat.api.serializers import (
    ConversationSerializer,
    MessageSerializer,
    SendMessageSerializer,
    StartConversationSerializer,
)
from apps.chat.application.services import (
    ListMessagesService,
    ListMyConversationsService,
    SendMessageService,
    StartDirectConversationService,
)
from apps.chat.domain.exceptions import NotAParticipantError
from apps.chat.infrastructure.django.repositories import DjangoChatRepository

_repository = DjangoChatRepository()


class StartConversationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = StartConversationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = StartDirectConversationService(repository=_repository)
        try:
            entity = service.start(
                user_id=request.user.id, other_user_id=serializer.validated_data["other_user_id"]
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(ConversationSerializer(asdict(entity)).data, status=201)


class MyConversationsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        service = ListMyConversationsService(repository=_repository)
        entities = service.list_for_user(request.user.id)
        return Response(ConversationSerializer([asdict(e) for e in entities], many=True).data)


class ConversationMessagesView(APIView):
    """
    REST history endpoint, used to load a conversation's backlog when the
    page first opens (before the WebSocket connection takes over for new,
    real-time messages) and to page further back ("load older messages").
    Also doubles as a fallback way to send a message for any client that
    can't or doesn't want to hold a WebSocket connection open.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, conversation_id):
        before_id = request.query_params.get("before_id")
        service = ListMessagesService(repository=_repository)
        try:
            entities = service.list_for_conversation(
                conversation_id=conversation_id,
                requester_id=request.user.id,
                before_id=int(before_id) if before_id else None,
            )
        except NotAParticipantError:
            return Response({"detail": "Not found"}, status=404)
        return Response(MessageSerializer([e.__dict__ for e in entities], many=True).data)

    def post(self, request, conversation_id):
        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = SendMessageService(repository=_repository)
        try:
            entity = service.send(
                conversation_id=conversation_id,
                sender_id=request.user.id,
                body=serializer.validated_data["body"],
            )
        except NotAParticipantError:
            return Response({"detail": "Not found"}, status=404)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(MessageSerializer(entity.__dict__).data, status=201)
