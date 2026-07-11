from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from apps.activity.domain.entities import ActivityLogEntry
from apps.activity.domain.ports import ActivityLogRepository


@dataclass
class RecordActivityService:
    """Use case: log one user action. Called from the middleware adapter."""

    repository: ActivityLogRepository

    def record(
        self, *, user_id: UUID | None, action: str, path: str, method: str, status_code: int
    ) -> ActivityLogEntry:
        return self.repository.record(
            user_id=user_id, action=action, path=path, method=method, status_code=status_code
        )


@dataclass
class ListUserActivityService:
    repository: ActivityLogRepository

    def list_for_user(self, user_id: UUID, limit: int = 50) -> list[ActivityLogEntry]:
        return self.repository.list_for_user(user_id, limit=limit)
