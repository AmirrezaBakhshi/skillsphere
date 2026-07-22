from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from apps.recommendations.domain.entities import ProjectRecommendation


class ProjectCatalogPort(ABC):
    """
    Read-only view of "ready" projects the recommendation engine can
    reason over: id, owner, tags, description. A separate port from
    apps.projects.domain.ports.ProjectRepository (Stage 2) on purpose -
    that one is about owning/mutating a single user's projects; this one
    is a read-only, cross-user catalog view, much like analytics'
    AnalyticsQueryPort from Stage 3. Keeping them separate means the
    recommendation engine's dependency is scoped to exactly what it
    needs and can't accidentally end up able to modify project data.
    """

    @abstractmethod
    def list_ready_projects(self) -> list[dict]:
        """Each dict: {id, title, owner_id, owner_username, tags: list[str], description}"""
        ...
