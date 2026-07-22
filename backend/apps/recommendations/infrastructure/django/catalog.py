from apps.projects.infrastructure.django.models import Project
from apps.recommendations.domain.ports import ProjectCatalogPort


class DjangoProjectCatalog(ProjectCatalogPort):
    def list_ready_projects(self) -> list[dict]:
        projects = Project.objects.filter(status="ready").select_related("owner").prefetch_related("tags")
        return [
            {
                "id": p.id,
                "title": p.title,
                "description": p.description,
                "owner_id": p.owner_id,
                "owner_username": p.owner.username,
                "tags": list(p.tags.values_list("name", flat=True)),
                "download_count": p.download_count,
            }
            for p in projects
        ]
