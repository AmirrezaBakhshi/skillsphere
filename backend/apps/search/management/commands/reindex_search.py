from django.core.management.base import BaseCommand

from apps.projects.infrastructure.django.models import Project
from apps.search.domain.entities import ProjectDocument, UserDocument
from apps.search.application.services import IndexProjectService, IndexUserService
from apps.search.infrastructure.elasticsearch.adapters import (
    ElasticsearchProjectSearch,
    ElasticsearchUserSearch,
)
from apps.search.infrastructure.elasticsearch.indices import ensure_indices
from apps.users.infrastructure.django.models import User


class Command(BaseCommand):
    help = (
        "Bulk-index all existing ready projects and users into Elasticsearch. "
        "Run this once after Stage 4 is deployed (or after wiping the ES data "
        "volume) - new records get indexed automatically going forward via "
        "Celery tasks, this command is only for backfilling history."
    )

    def handle(self, *args, **options):
        ensure_indices()

        project_indexer = IndexProjectService(repository=ElasticsearchProjectSearch())
        projects = Project.objects.filter(status="ready").select_related("owner")
        for project in projects:
            project_indexer.index(
                ProjectDocument(
                    id=project.id,
                    title=project.title,
                    description=project.description,
                    tags=list(project.tags.values_list("name", flat=True)),
                    owner_id=project.owner_id,
                    owner_username=project.owner.username,
                    status=project.status,
                )
            )
        self.stdout.write(self.style.SUCCESS(f"Indexed {projects.count()} projects"))

        user_indexer = IndexUserService(repository=ElasticsearchUserSearch())
        users = User.objects.all()
        for user in users:
            user_indexer.index(UserDocument(id=user.id, username=user.username, bio=user.bio))
        self.stdout.write(self.style.SUCCESS(f"Indexed {users.count()} users"))
