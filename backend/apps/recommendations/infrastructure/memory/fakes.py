from apps.recommendations.domain.ports import ProjectCatalogPort


class InMemoryProjectCatalog(ProjectCatalogPort):
    """A fake catalog for testing GetRecommendationsForUserService without a database."""

    def __init__(self, projects: list[dict] | None = None):
        self._projects = projects or []

    def list_ready_projects(self) -> list[dict]:
        return self._projects
