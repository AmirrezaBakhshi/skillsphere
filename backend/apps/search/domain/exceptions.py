class SearchUnavailableError(Exception):
    """
    Raised when the search backend (Elasticsearch) can't be reached.
    Mapped to HTTP 503 by the API layer - a search outage should degrade
    gracefully, not look like a bug in our own code (400/500).
    """
