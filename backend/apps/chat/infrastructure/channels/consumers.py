from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from apps.chat.application.services import ListMessagesService, SendMessageService
from apps.chat.domain.exceptions import NotAParticipantError
from apps.chat.infrastructure.django.repositories import DjangoChatRepository


class ChatConsumer(AsyncJsonWebsocketConsumer):
    """
    One instance of this class exists per open WebSocket connection.
    Messages are broadcast via the channel layer's "group" mechanism:
    every consumer connected to the same conversation joins a group named
    after that conversation's id, and sending a message fans it out to
    everyone in the group (including, in a multi-server deployment,
    consumers connected to a *different* backend process entirely - that
    fan-out across processes is exactly what Redis, as the channel
    layer's backing store, makes possible).
    """

    async def connect(self):
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        self.group_name = f"conversation_{self.conversation_id}"
        user = self.scope["user"]

        if not user.is_authenticated:
            await self.close(code=4001)
            return

        is_participant = await self._is_participant(user.id)
        if not is_participant:
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        body = content.get("body", "")
        user = self.scope["user"]

        try:
            message = await self._send_message(user.id, body)
        except (ValueError, NotAParticipantError) as exc:
            await self.send_json({"type": "error", "detail": str(exc)})
            return

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "chat.message",
                "message": {
                    "id": message.id,
                    "conversation_id": str(message.conversation_id),
                    "sender_id": str(message.sender_id),
                    "sender_username": message.sender_username,
                    "body": message.body,
                    "created_at": message.created_at.isoformat(),
                },
            },
        )

    async def chat_message(self, event):
        """Handler name matches the "type" field ("chat.message" -> chat_message) -
        this is Channels' own dispatch convention for group_send events."""
        await self.send_json({"type": "message", "message": event["message"]})

    @database_sync_to_async
    def _is_participant(self, user_id) -> bool:
        repository = DjangoChatRepository()
        return (
            repository.get_conversation_for_participant(
                conversation_id=self.conversation_id, user_id=user_id
            )
            is not None
        )

    @database_sync_to_async
    def _send_message(self, sender_id, body):
        service = SendMessageService(repository=DjangoChatRepository())
        return service.send(conversation_id=self.conversation_id, sender_id=sender_id, body=body)
