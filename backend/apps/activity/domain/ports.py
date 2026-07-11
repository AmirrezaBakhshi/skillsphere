from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from apps.activity.domain.entities import ActivityLogEntry


class ActivityLogRepository(ABC):
    @abstractmethod
    def record(
        self, *, user_id: UUID | None, action: str, path: str, method: str, status_code: int
    ) -> ActivityLogEntry:
        ...

    @abstractmethod
    def list_for_user(self, user_id: UUID, limit: int = 50) -> list[ActivityLogEntry]:
        ...
