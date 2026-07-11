from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from apps.notifications.domain.entities import NotificationEntity
from apps.notifications.domain.exceptions import NotificationNotFoundError
from apps.notifications.domain.ports import NotificationRepository


@dataclass
class NotifyUserService:
    """Use case: create a notification for one user."""

    repository: NotificationRepository

    def notify(self, *, user_id: UUID, verb: str, message: str, level: str = "info") -> NotificationEntity:
        return self.repository.create(user_id=user_id, verb=verb, message=message, level=level)


@dataclass
class ListNotificationsService:
    repository: NotificationRepository

    def list_for_user(self, user_id: UUID, unread_only: bool = False) -> list[NotificationEntity]:
        return self.repository.list_for_user(user_id, unread_only=unread_only)


@dataclass
class MarkNotificationReadService:
    repository: NotificationRepository

    def mark_read(self, *, notification_id: int, user_id: UUID) -> NotificationEntity:
        entry = self.repository.mark_read(notification_id=notification_id, user_id=user_id)
        if entry is None:
            raise NotificationNotFoundError(f"No notification {notification_id} for this user")
        return entry
