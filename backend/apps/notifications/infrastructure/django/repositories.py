from __future__ import annotations

from uuid import UUID

from apps.notifications.domain.entities import NotificationEntity
from apps.notifications.domain.ports import NotificationRepository
from apps.notifications.infrastructure.django.models import Notification


class DjangoNotificationRepository(NotificationRepository):
    def create(self, *, user_id: UUID, verb: str, message: str, level: str = "info") -> NotificationEntity:
        row = Notification.objects.create(user_id=user_id, verb=verb, message=message, level=level)
        return self._to_entity(row)

    def list_for_user(self, user_id: UUID, unread_only: bool = False) -> list[NotificationEntity]:
        qs = Notification.objects.filter(user_id=user_id)
        if unread_only:
            qs = qs.filter(is_read=False)
        return [self._to_entity(row) for row in qs]

    def mark_read(self, *, notification_id: int, user_id: UUID) -> NotificationEntity | None:
        updated = Notification.objects.filter(id=notification_id, user_id=user_id).update(is_read=True)
        if not updated:
            return None
        row = Notification.objects.get(id=notification_id)
        return self._to_entity(row)

    @staticmethod
    def _to_entity(row: Notification) -> NotificationEntity:
        return NotificationEntity(
            id=row.id,
            user_id=row.user_id,
            verb=row.verb,
            message=row.message,
            level=row.level,
            is_read=row.is_read,
            created_at=row.created_at,
        )
