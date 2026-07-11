from __future__ import annotations

from typing import BinaryIO
from uuid import UUID

from apps.projects.domain.entities import ProjectEntity
from apps.projects.domain.ports import ProjectRepository
from apps.projects.infrastructure.django.models import Project


class DjangoProjectRepository(ProjectRepository):
    def create(
        self,
        *,
        owner_id: UUID,
        title: str,
        description: str,
        file: BinaryIO,
        file_name: str,
        file_size: int,
        content_type: str,
    ) -> ProjectEntity:
        project = Project(
            owner_id=owner_id,
            title=title,
            description=description,
            file_size=file_size,
            content_type=content_type,
            status="pending",
        )
        project.file.save(file_name, file, save=True)
        return self._to_entity(project)

    def get_for_owner(self, *, project_id: UUID, owner_id: UUID) -> ProjectEntity | None:
        project = Project.objects.filter(id=project_id, owner_id=owner_id).first()
        return self._to_entity(project) if project else None

    def get_file_path(self, project_id: UUID) -> str | None:
        project = Project.objects.filter(id=project_id).first()
        if not project or not project.file:
            return None
        return project.file.path

    def list_for_owner(self, owner_id: UUID) -> list[ProjectEntity]:
        return [self._to_entity(p) for p in Project.objects.filter(owner_id=owner_id)]

    def set_status(self, *, project_id: UUID, status: str) -> None:
        Project.objects.filter(id=project_id).update(status=status)

    @staticmethod
    def _to_entity(project: Project) -> ProjectEntity:
        return ProjectEntity(
            id=project.id,
            owner_id=project.owner_id,
            title=project.title,
            description=project.description,
            file_name=project.file.name.rsplit("/", 1)[-1] if project.file else "",
            file_size=project.file_size,
            content_type=project.content_type,
            status=project.status,
            created_at=project.created_at,
        )
