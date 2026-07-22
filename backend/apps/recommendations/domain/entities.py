from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass
class ProjectRecommendation:
    project_id: UUID
    title: str
    owner_username: str
    shared_tags: list[str]
    score: float
    reason: str
