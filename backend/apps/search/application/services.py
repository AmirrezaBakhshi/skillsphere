from __future__ import annotations

from dataclasses import dataclass

from apps.search.domain.entities import (
    ProjectDocument,
    ProjectSearchResult,
    UserDocument,
    UserSearchResult,
)
from apps.search.domain.ports import ProjectSearchPort, UserSearchPort


@dataclass
class IndexProjectService:
    repository: ProjectSearchPort

    def index(self, document: ProjectDocument) -> None:
        self.repository.index_project(document)


@dataclass
class SearchProjectsService:
    repository: ProjectSearchPort

    def search(self, query: str, limit: int = 20) -> list[ProjectSearchResult]:
        query = query.strip()
        if not query:
            return []
        return self.repository.search_projects(query, limit=limit)


@dataclass
class IndexUserService:
    repository: UserSearchPort

    def index(self, document: UserDocument) -> None:
        self.repository.index_user(document)


@dataclass
class SearchUsersService:
    repository: UserSearchPort

    def search(self, query: str, limit: int = 20) -> list[UserSearchResult]:
        query = query.strip()
        if not query:
            return []
        return self.repository.search_users(query, limit=limit)
