from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID


@dataclass
class ProjectSearchResult:
    id: UUID
    title: str
    description: str
    tags: list[str]
    owner_username: str
    score: float


@dataclass
class UserSearchResult:
    id: UUID
    username: str
    bio: str
    score: float


@dataclass
class ProjectDocument:
    """What gets written into the projects search index - a deliberately
    flat, denormalized shape (owner_username inlined rather than just an
    owner_id) since search indices are read-optimized, not relational."""

    id: UUID
    title: str
    description: str
    tags: list[str] = field(default_factory=list)
    owner_id: UUID | None = None
    owner_username: str = ""
    status: str = "ready"


@dataclass
class UserDocument:
    id: UUID
    username: str
    bio: str = ""
