from celery import shared_task

from apps.search.domain.entities import ProjectDocument, UserDocument
from apps.search.domain.exceptions import SearchUnavailableError
from apps.search.application.services import IndexProjectService, IndexUserService
from apps.search.infrastructure.elasticsearch.adapters import (
    ElasticsearchProjectSearch,
    ElasticsearchUserSearch,
)
from apps.search.infrastructure.elasticsearch.indices import ensure_indices


@shared_task(bind=True, max_retries=5, default_retry_delay=15)
def index_project_task(self, project_id):
    from apps.projects.infrastructure.django.models import Project

    project = Project.objects.filter(id=project_id).select_related("owner").first()
    if not project or project.status != "ready":
        return

    document = ProjectDocument(
        id=project.id,
        title=project.title,
        description=project.description,
        tags=list(project.tags.values_list("name", flat=True)),
        owner_id=project.owner_id,
        owner_username=project.owner.username,
        status=project.status,
    )

    try:
        ensure_indices()
        IndexProjectService(repository=ElasticsearchProjectSearch()).index(document)
    except SearchUnavailableError as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=5, default_retry_delay=15)
def index_user_task(self, user_id):
    from apps.users.infrastructure.django.models import User

    user = User.objects.filter(id=user_id).first()
    if not user:
        return

    document = UserDocument(id=user.id, username=user.username, bio=user.bio)

    try:
        ensure_indices()
        IndexUserService(repository=ElasticsearchUserSearch()).index(document)
    except SearchUnavailableError as exc:
        raise self.retry(exc=exc)
