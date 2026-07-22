from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from apps.chat.domain.entities import ConversationEntity, MessageEntity


class ChatRepository(ABC):
    @abstractmethod
    def get_or_create_direct_conversation(
        self, *, user_a_id: UUID, user_b_id: UUID
    ) -> ConversationEntity:
        ...

    @abstractmethod
    def list_conversations_for_user(self, user_id: UUID) -> list[ConversationEntity]:
        ...

    @abstractmethod
    def get_conversation_for_participant(
        self, *, conversation_id: UUID, user_id: UUID
    ) -> ConversationEntity | None:
        ...

    @abstractmethod
    def add_message(
        self, *, conversation_id: UUID, sender_id: UUID, body: str
    ) -> MessageEntity:
        ...

    @abstractmethod
    def list_messages(
        self, *, conversation_id: UUID, limit: int = 50, before_id: int | None = None
    ) -> list[MessageEntity]:
        ...
