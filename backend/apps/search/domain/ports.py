from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from apps.search.domain.entities import (
    ProjectDocument,
    ProjectSearchResult,
    UserDocument,
    UserSearchResult,
)


class ProjectSearchPort(ABC):
    @abstractmethod
    def index_project(self, document: ProjectDocument) -> None:
        ...

    @abstractmethod
    def search_projects(self, query: str, limit: int = 20) -> list[ProjectSearchResult]:
        ...


class UserSearchPort(ABC):
    @abstractmethod
    def index_user(self, document: UserDocument) -> None:
        ...

    @abstractmethod
    def search_users(self, query: str, limit: int = 20) -> list[UserSearchResult]:
        ...
