from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class MessageEntity:
    id: int | None
    conversation_id: UUID
    sender_id: UUID
    sender_username: str
    body: str
    created_at: datetime | None = None


@dataclass
class ConversationEntity:
    id: UUID | None
    participant_ids: list[UUID] = field(default_factory=list)
    project_id: UUID | None = None  # set when the chat is scoped to a project's collaborators
    created_at: datetime | None = None
    last_message: MessageEntity | None = None
