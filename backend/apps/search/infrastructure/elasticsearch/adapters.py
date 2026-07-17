from __future__ import annotations

from elasticsearch.exceptions import ConnectionError as ESConnectionError
from elasticsearch.exceptions import ConnectionTimeout, TransportError

from apps.search.domain.entities import (
    ProjectDocument,
    ProjectSearchResult,
    UserDocument,
    UserSearchResult,
)
from apps.search.domain.exceptions import SearchUnavailableError
from apps.search.domain.ports import ProjectSearchPort, UserSearchPort
from apps.search.infrastructure.elasticsearch.client import get_es_client
from apps.search.infrastructure.elasticsearch.indices import PROJECTS_INDEX, USERS_INDEX

_ES_ERRORS = (ESConnectionError, ConnectionTimeout, TransportError)


class ElasticsearchProjectSearch(ProjectSearchPort):
    def index_project(self, document: ProjectDocument) -> None:
        es = get_es_client()
        try:
            es.index(
                index=PROJECTS_INDEX,
                id=str(document.id),
                body={
                    "title": document.title,
                    "description": document.description,
                    "tags": document.tags,
                    "owner_id": str(document.owner_id) if document.owner_id else None,
                    "owner_username": document.owner_username,
                    "status": document.status,
                },
            )
        except _ES_ERRORS as exc:
            raise SearchUnavailableError("Search index is unreachable") from exc

    def search_projects(self, query: str, limit: int = 20) -> list[ProjectSearchResult]:
        es = get_es_client()
        try:
            response = es.search(
                index=PROJECTS_INDEX,
                body={
                    "size": limit,
                    "query": {
                        "bool": {
                            "must": {
                                "multi_match": {
                                    "query": query,
                                    "fields": ["title^3", "description", "tags^2"],
                                    "fuzziness": "AUTO",
                                }
                            },
                            # Only surface projects that finished processing -
                            # a "pending"/"rejected" upload shouldn't show up
                            # in someone else's search results.
                            "filter": {"term": {"status": "ready"}},
                        }
                    },
                },
            )
        except _ES_ERRORS as exc:
            raise SearchUnavailableError("Search index is unreachable") from exc

        return [
            ProjectSearchResult(
                id=hit["_id"],
                title=hit["_source"]["title"],
                description=hit["_source"]["description"],
                tags=hit["_source"].get("tags", []),
                owner_username=hit["_source"].get("owner_username", ""),
                score=hit["_score"],
            )
            for hit in response["hits"]["hits"]
        ]


class ElasticsearchUserSearch(UserSearchPort):
    def index_user(self, document: UserDocument) -> None:
        es = get_es_client()
        try:
            es.index(
                index=USERS_INDEX,
                id=str(document.id),
                body={"username": document.username, "bio": document.bio},
            )
        except _ES_ERRORS as exc:
            raise SearchUnavailableError("Search index is unreachable") from exc

    def search_users(self, query: str, limit: int = 20) -> list[UserSearchResult]:
        es = get_es_client()
        try:
            response = es.search(
                index=USERS_INDEX,
                body={
                    "size": limit,
                    "query": {
                        "multi_match": {
                            "query": query,
                            "fields": ["username^2", "bio"],
                            "fuzziness": "AUTO",
                        }
                    },
                },
            )
        except _ES_ERRORS as exc:
            raise SearchUnavailableError("Search index is unreachable") from exc

        return [
            UserSearchResult(
                id=hit["_id"],
                username=hit["_source"]["username"],
                bio=hit["_source"].get("bio", ""),
                score=hit["_score"],
            )
            for hit in response["hits"]["hits"]
        ]
