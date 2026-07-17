import uuid

from apps.search.application.services import (
    IndexProjectService,
    IndexUserService,
    SearchProjectsService,
    SearchUsersService,
)
from apps.search.domain.entities import ProjectDocument, UserDocument
from apps.search.infrastructure.memory.fakes import InMemoryProjectSearch, InMemoryUserSearch


def test_search_finds_a_project_by_title_word():
    repository = InMemoryProjectSearch()
    IndexProjectService(repository).index(
        ProjectDocument(
            id=uuid.uuid4(),
            title="Offline-first recipe app",
            description="A PWA for saving recipes without internet",
            tags=["react", "pwa"],
            owner_username="amy",
            status="ready",
        )
    )

    results = SearchProjectsService(repository).search("recipe")

    assert len(results) == 1
    assert results[0].title == "Offline-first recipe app"


def test_search_finds_a_project_by_tag():
    repository = InMemoryProjectSearch()
    IndexProjectService(repository).index(
        ProjectDocument(
            id=uuid.uuid4(),
            title="Rate-limited job queue",
            description="A Redis-backed queue with backoff",
            tags=["python", "redis"],
            owner_username="devon",
            status="ready",
        )
    )

    results = SearchProjectsService(repository).search("redis")

    assert len(results) == 1
    assert results[0].owner_username == "devon"


def test_search_ignores_projects_that_arent_ready():
    repository = InMemoryProjectSearch()
    IndexProjectService(repository).index(
        ProjectDocument(
            id=uuid.uuid4(),
            title="Broken upload",
            description="still processing",
            tags=[],
            owner_username="theo",
            status="pending",
        )
    )

    results = SearchProjectsService(repository).search("broken")

    assert results == []


def test_search_with_blank_query_returns_nothing():
    repository = InMemoryProjectSearch()
    results = SearchProjectsService(repository).search("   ")
    assert results == []


def test_user_search_matches_bio():
    repository = InMemoryUserSearch()
    IndexUserService(repository).index(
        UserDocument(id=uuid.uuid4(), username="priya", bio="I build Django APIs for fun")
    )

    results = SearchUsersService(repository).search("django")

    assert len(results) == 1
    assert results[0].username == "priya"
