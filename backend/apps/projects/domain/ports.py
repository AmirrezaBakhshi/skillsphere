from __future__ import annotations

from abc import ABC, abstractmethod
from typing import BinaryIO
from uuid import UUID

from apps.projects.domain.entities import ProjectEntity


class ProjectRepository(ABC):
    @abstractmethod
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
        tags: list[str] = (),
    ) -> ProjectEntity:
        ...

    @abstractmethod
    def get_for_owner(self, *, project_id: UUID, owner_id: UUID) -> ProjectEntity | None:
        ...

    @abstractmethod
    def get_file_path(self, project_id: UUID) -> str | None:
        ...

    @abstractmethod
    def list_for_owner(self, owner_id: UUID) -> list[ProjectEntity]:
        ...

    @abstractmethod
    def set_status(self, *, project_id: UUID, status: str) -> None:
        ...
