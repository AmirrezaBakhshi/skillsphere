from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class ProjectEntity:
    id: UUID | None
    owner_id: UUID
    title: str
    description: str
    file_name: str
    file_size: int
    content_type: str
    status: str  # "pending" | "processing" | "ready" | "rejected"
    download_count: int = 0
    tags: list[str] = field(default_factory=list)
    created_at: datetime | None = None
