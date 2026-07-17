from elasticsearch.exceptions import RequestError

from apps.search.infrastructure.elasticsearch.client import get_es_client

PROJECTS_INDEX = "skillsphere_projects"
USERS_INDEX = "skillsphere_users"

_PROJECTS_MAPPING = {
    "mappings": {
        "properties": {
            "title": {"type": "text"},
            "description": {"type": "text"},
            "tags": {"type": "keyword"},
            "owner_id": {"type": "keyword"},
            "owner_username": {"type": "keyword"},
            "status": {"type": "keyword"},
        }
    }
}

_USERS_MAPPING = {
    "mappings": {
        "properties": {
            "username": {"type": "text"},
            "bio": {"type": "text"},
        }
    }
}


def ensure_indices() -> None:
    """
    Idempotent - safe to call on every app/worker startup, or from the
    reindex_search management command. Elasticsearch itself would 400 if
    you try to create an index that already exists, so we check first
    (a plain create-if-missing, not a schema migration tool - if you
    change a mapping later you'd need to reindex into a new index name).
    """
    es = get_es_client()
    for index_name, mapping in ((PROJECTS_INDEX, _PROJECTS_MAPPING), (USERS_INDEX, _USERS_MAPPING)):
        if not es.indices.exists(index=index_name):
            try:
                es.indices.create(index=index_name, body=mapping)
            except RequestError as exc:
                # Race: another process created it between our exists()
                # check and this call - fine, nothing to do.
                if exc.error != "resource_already_exists_exception":
                    raise
