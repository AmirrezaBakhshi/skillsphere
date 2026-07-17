from django.conf import settings
from elasticsearch import Elasticsearch

_client: Elasticsearch | None = None


def get_es_client() -> Elasticsearch:
    """
    A single shared client per process, rather than a new connection per
    request. The client itself is lazy/lightweight (it doesn't open a
    persistent connection until a request is actually made), so this is
    just about avoiding rebuilding config repeatedly.
    """
    global _client
    if _client is None:
        _client = Elasticsearch([settings.ELASTICSEARCH_URL])
    return _client
