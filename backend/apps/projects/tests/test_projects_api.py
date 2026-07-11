import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile


@pytest.mark.django_db
def test_upload_project_succeeds_and_becomes_ready(authed_client):
    file = SimpleUploadedFile("notes.pdf", b"%PDF-1.4 fake pdf content", content_type="application/pdf")

    response = authed_client.post(
        "/api/v1/projects/upload/",
        {"title": "My Notes", "description": "some notes", "file": file},
        format="multipart",
    )

    assert response.status_code == 201
    assert response.data["title"] == "My Notes"
    # The response is built from the entity as of creation time, before the
    # background task runs - so it's correctly "pending" here even though
    # Celery has already finished processing it (eager mode) by now.
    assert response.data["status"] == "pending"

    listing = authed_client.get("/api/v1/projects/mine/")
    assert listing.data[0]["status"] == "ready"


@pytest.mark.django_db
def test_upload_rejects_disallowed_content_type(authed_client):
    file = SimpleUploadedFile("virus.exe", b"MZ...", content_type="application/x-msdownload")

    response = authed_client.post(
        "/api/v1/projects/upload/",
        {"title": "Bad file", "file": file},
        format="multipart",
    )

    assert response.status_code == 422


@pytest.mark.django_db
def test_upload_rejects_oversized_file(authed_client, settings):
    settings.PROJECT_UPLOAD_MAX_SIZE_BYTES = 10
    file = SimpleUploadedFile("big.pdf", b"x" * 100, content_type="application/pdf")

    response = authed_client.post(
        "/api/v1/projects/upload/",
        {"title": "Too big", "file": file},
        format="multipart",
    )

    assert response.status_code == 422


@pytest.mark.django_db
def test_list_mine_only_shows_own_projects(authed_client):
    file = SimpleUploadedFile("a.pdf", b"content", content_type="application/pdf")
    authed_client.post(
        "/api/v1/projects/upload/", {"title": "A", "file": file}, format="multipart"
    )

    response = authed_client.get("/api/v1/projects/mine/")
    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]["title"] == "A"


@pytest.mark.django_db
def test_download_requires_ownership(authed_client):
    import uuid

    response = authed_client.get(f"/api/v1/projects/{uuid.uuid4()}/download/")
    assert response.status_code == 404
