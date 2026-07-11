from __future__ import annotations

from uuid import UUID

from apps.activity.domain.entities import ActivityLogEntry
from apps.activity.domain.ports import ActivityLogRepository
from apps.activity.infrastructure.django.models import ActivityLog


class DjangoActivityLogRepository(ActivityLogRepository):
    def record(
        self, *, user_id: UUID | None, action: str, path: str, method: str, status_code: int
    ) -> ActivityLogEntry:
        entry = ActivityLog.objects.create(
            user_id=user_id, action=action, path=path, method=method, status_code=status_code
        )
        return self._to_entity(entry)

    def list_for_user(self, user_id: UUID, limit: int = 50) -> list[ActivityLogEntry]:
        rows = ActivityLog.objects.filter(user_id=user_id)[:limit]
        return [self._to_entity(row) for row in rows]

    @staticmethod
    def _to_entity(row: ActivityLog) -> ActivityLogEntry:
        return ActivityLogEntry(
            id=row.id,
            user_id=row.user_id,
            action=row.action,
            path=row.path,
            method=row.method,
            status_code=row.status_code,
            created_at=row.created_at,
        )
