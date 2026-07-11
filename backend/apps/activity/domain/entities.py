from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class ActivityLogEntry:
    """One recorded user action - a login, an upload, a hit against the API."""

    id: int | None
    user_id: UUID | None
    action: str
    path: str
    method: str
    status_code: int
    created_at: datetime | None = None
