from __future__ import annotations

from apps.search.domain.entities import (
    ProjectDocument,
    ProjectSearchResult,
    UserDocument,
    UserSearchResult,
)
from apps.search.domain.ports import ProjectSearchPort, UserSearchPort


class InMemoryProjectSearch(ProjectSearchPort):
    """
    A fake standing in for Elasticsearch: a plain dict plus a naive
    substring match instead of a real inverted-text-index search engine.
    Good enough to prove IndexProjectService/SearchProjectsService's
    logic is correct without a running Elasticsearch server - this is
    the whole point of depending on ProjectSearchPort (an abstraction)
    rather than importing the Elasticsearch adapter directly.
    """

    def __init__(self):
        self._documents: dict[str, ProjectDocument] = {}

    def index_project(self, document: ProjectDocument) -> None:
        self._documents[str(document.id)] = document

    def search_projects(self, query: str, limit: int = 20) -> list[ProjectSearchResult]:
        query_lower = query.lower()
        results = []
        for doc in self._documents.values():
            if doc.status != "ready":
                continue
            haystack = f"{doc.title} {doc.description} {' '.join(doc.tags)}".lower()
            if query_lower in haystack:
                results.append(
                    ProjectSearchResult(
                        id=doc.id,
                        title=doc.title,
                        description=doc.description,
                        tags=doc.tags,
                        owner_username=doc.owner_username,
                        score=1.0,
                    )
                )
        return results[:limit]


class InMemoryUserSearch(UserSearchPort):
    def __init__(self):
        self._documents: dict[str, UserDocument] = {}

    def index_user(self, document: UserDocument) -> None:
        self._documents[str(document.id)] = document

    def search_users(self, query: str, limit: int = 20) -> list[UserSearchResult]:
        query_lower = query.lower()
        results = []
        for doc in self._documents.values():
            haystack = f"{doc.username} {doc.bio}".lower()
            if query_lower in haystack:
                results.append(
                    UserSearchResult(id=doc.id, username=doc.username, bio=doc.bio, score=1.0)
                )
        return results[:limit]
