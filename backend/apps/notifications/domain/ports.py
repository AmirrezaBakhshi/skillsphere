from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from apps.notifications.domain.entities import NotificationEntity


class NotificationRepository(ABC):
    @abstractmethod
    def create(self, *, user_id: UUID, verb: str, message: str, level: str = "info") -> NotificationEntity:
        ...

    @abstractmethod
    def list_for_user(self, user_id: UUID, unread_only: bool = False) -> list[NotificationEntity]:
        ...

    @abstractmethod
    def mark_read(self, *, notification_id: int, user_id: UUID) -> NotificationEntity | None:
        ...
