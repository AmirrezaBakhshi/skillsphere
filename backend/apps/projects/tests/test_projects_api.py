import io
import uuid

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient


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
    file = SimpleUploadedFile("a.pdf", b"%PDF-1.4\\n%\\xe2\\xe3\\xcf\\xd3\\n1 0 obj\\n<< /Type /Catalog >>\\nendobj\\n%%EOF", content_type="application/pdf")
    authed_client.post(
        "/api/v1/projects/upload/", {"title": "A", "file": file}, format="multipart"
    )

    response = authed_client.get("/api/v1/projects/mine/")
    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]["title"] == "A"


@pytest.mark.django_db
def test_download_requires_ownership(authed_client):
    response = authed_client.get(f"/api/v1/projects/{uuid.uuid4()}/download/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_project_download_is_owner_only_and_not_cacheable(authed_client):
    uploaded = SimpleUploadedFile(
        "private-notes.pdf",
        b"%PDF-1.4\\nprivate test document\\n%%EOF",
        content_type="application/pdf",
    )
    upload_response = authed_client.post(
        "/api/v1/projects/upload/",
        {"title": "Private notes", "file": uploaded},
        format="multipart",
    )
    assert upload_response.status_code == 201
    project_id = upload_response.data["id"]

    # A different authenticated account must not be able to download the file.
    outsider = APIClient()
    registration = outsider.post(
        "/api/v1/auth/register/",
        {
            "email": "project-outsider@example.com",
            "username": "project-outsider",
            "password": "S3curePass!23",
        },
        format="json",
    )
    assert registration.status_code == 200
    outsider.credentials(HTTP_AUTHORIZATION=f"Bearer {registration.data['access']}")
    denied = outsider.get(f"/api/v1/projects/{project_id}/download/")
    assert denied.status_code == 404

    # The owner can still download it, but the response must not be cached
    # or interpreted as inline active content by browsers.
    allowed = authed_client.get(f"/api/v1/projects/{project_id}/download/")
    assert allowed.status_code == 200
    assert allowed["Cache-Control"] == "private, no-store"
    assert allowed["X-Content-Type-Options"] == "nosniff"
    assert "attachment" in allowed["Content-Disposition"]
    assert b"private test document" in b"".join(allowed.streaming_content)


@pytest.mark.parametrize(
    ("filename", "content", "content_type"),
    [
        ("fake.pdf", b"MZ\\x90\\x00not a PDF", "application/pdf"),
        ("fake.png", b"\\xff\\xd8\\xffnot a PNG", "image/png"),
        ("fake.zip", b"not a ZIP archive", "application/zip"),
    ],
)
@pytest.mark.django_db
def test_upload_rejects_content_type_spoofing(authed_client, filename, content, content_type):
    file = SimpleUploadedFile(filename, content, content_type=content_type)

    response = authed_client.post(
        "/api/v1/projects/upload/",
        {"title": "Spoofed upload", "file": file},
        format="multipart",
    )

    assert response.status_code == 422
