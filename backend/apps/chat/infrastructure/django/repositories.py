from __future__ import annotations

from uuid import UUID

from django.contrib.auth import get_user_model

from apps.chat.domain.entities import ConversationEntity, MessageEntity
from apps.chat.domain.ports import ChatRepository
from apps.chat.infrastructure.django.models import Conversation, Message

User = get_user_model()


class DjangoChatRepository(ChatRepository):
    def get_or_create_direct_conversation(
        self, *, user_a_id: UUID, user_b_id: UUID
    ) -> ConversationEntity:
        # A "direct" conversation is one with exactly these two participants
        # and no project scope. We fetch candidates sharing user_a as a
        # participant, then compare each one's actual participant set in
        # Python - deliberately not done as a single annotated queryset
        # (chaining .filter(participants__id=...) twice plus
        # Count("participants") multiplies across the resulting joins and
        # silently gives the wrong count). At this scale - one person's
        # direct conversations - fetching candidates and comparing sets is
        # simple and correct; it would need revisiting only if a single
        # user could plausibly have thousands of direct conversations.
        candidates = Conversation.objects.filter(
            project=None, participants__id=user_a_id
        ).prefetch_related("participants")

        target = {user_a_id, user_b_id}
        for candidate in candidates:
            participant_ids = set(candidate.participants.values_list("id", flat=True))
            if participant_ids == target:
                return self._to_entity(candidate)

        conversation = Conversation.objects.create()
        conversation.participants.set([user_a_id, user_b_id])
        return self._to_entity(conversation)

    def list_conversations_for_user(self, user_id: UUID) -> list[ConversationEntity]:
        conversations = Conversation.objects.filter(participants__id=user_id).prefetch_related(
            "participants"
        )
        return [self._to_entity(c) for c in conversations]

    def get_conversation_for_participant(
        self, *, conversation_id: UUID, user_id: UUID
    ) -> ConversationEntity | None:
        conversation = Conversation.objects.filter(
            id=conversation_id, participants__id=user_id
        ).first()
        return self._to_entity(conversation) if conversation else None

    def add_message(self, *, conversation_id: UUID, sender_id: UUID, body: str) -> MessageEntity:
        message = Message.objects.create(
            conversation_id=conversation_id, sender_id=sender_id, body=body
        )
        return self._message_to_entity(message)

    def list_messages(
        self, *, conversation_id: UUID, limit: int = 50, before_id: int | None = None
    ) -> list[MessageEntity]:
        qs = Message.objects.filter(conversation_id=conversation_id).select_related("sender")
        if before_id is not None:
            qs = qs.filter(id__lt=before_id)
        # Fetch newest-first for pagination, then re-reverse to chronological
        # order for display - this is what lets "load older messages" work
        # with a simple id cursor instead of offset-based paging.
        messages = list(qs.order_by("-id")[:limit])
        messages.reverse()
        return [self._message_to_entity(m) for m in messages]

    @staticmethod
    def _to_entity(conversation: Conversation) -> ConversationEntity:
        last = conversation.messages.select_related("sender").last()
        return ConversationEntity(
            id=conversation.id,
            participant_ids=list(conversation.participants.values_list("id", flat=True)),
            project_id=conversation.project_id,
            created_at=conversation.created_at,
            last_message=DjangoChatRepository._message_to_entity(last) if last else None,
        )

    @staticmethod
    def _message_to_entity(message: Message) -> MessageEntity:
        return MessageEntity(
            id=message.id,
            conversation_id=message.conversation_id,
            sender_id=message.sender_id,
            sender_username=message.sender.username,
            body=message.body,
            created_at=message.created_at,
        )
