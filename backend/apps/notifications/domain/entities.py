from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class NotificationEntity:
    id: int | None
    user_id: UUID
    verb: str
    message: str
    level: str  # "info" | "success" | "error"
    is_read: bool
    created_at: datetime | None = None
