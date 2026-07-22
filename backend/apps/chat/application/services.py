from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from apps.chat.domain.entities import ConversationEntity, MessageEntity
from apps.chat.domain.exceptions import NotAParticipantError
from apps.chat.domain.ports import ChatRepository

MAX_MESSAGE_LENGTH = 4000


@dataclass
class StartDirectConversationService:
    """Use case: get (or lazily create) the 1:1 conversation between two users."""

    repository: ChatRepository

    def start(self, *, user_id: UUID, other_user_id: UUID) -> ConversationEntity:
        if user_id == other_user_id:
            raise ValueError("Can't start a conversation with yourself")
        return self.repository.get_or_create_direct_conversation(
            user_a_id=user_id, user_b_id=other_user_id
        )


@dataclass
class ListMyConversationsService:
    repository: ChatRepository

    def list_for_user(self, user_id: UUID) -> list[ConversationEntity]:
        return self.repository.list_conversations_for_user(user_id)


@dataclass
class SendMessageService:
    """
    Use case: post a message into a conversation. Called from both the
    REST fallback endpoint and the WebSocket consumer, so validation
    (participant check, length limit) lives here exactly once rather than
    being duplicated - or worse, only enforced in one of the two places.
    """

    repository: ChatRepository

    def send(self, *, conversation_id: UUID, sender_id: UUID, body: str) -> MessageEntity:
        body = body.strip()
        if not body:
            raise ValueError("Message body can't be empty")
        if len(body) > MAX_MESSAGE_LENGTH:
            raise ValueError(f"Message exceeds {MAX_MESSAGE_LENGTH} characters")

        conversation = self.repository.get_conversation_for_participant(
            conversation_id=conversation_id, user_id=sender_id
        )
        if conversation is None:
            raise NotAParticipantError("You're not part of this conversation")

        return self.repository.add_message(
            conversation_id=conversation_id, sender_id=sender_id, body=body
        )


@dataclass
class ListMessagesService:
    repository: ChatRepository

    def list_for_conversation(
        self, *, conversation_id: UUID, requester_id: UUID, limit: int = 50, before_id: int | None = None
    ) -> list[MessageEntity]:
        conversation = self.repository.get_conversation_for_participant(
            conversation_id=conversation_id, user_id=requester_id
        )
        if conversation is None:
            raise NotAParticipantError("You're not part of this conversation")

        return self.repository.list_messages(
            conversation_id=conversation_id, limit=limit, before_id=before_id
        )
