import pytest
from django.core.files.uploadedfile import SimpleUploadedFile


@pytest.mark.django_db
def test_user_dashboard_reflects_uploaded_projects(authed_client):
    file = SimpleUploadedFile("notes.pdf", b"content", content_type="application/pdf")
    authed_client.post(
        "/api/v1/projects/upload/", {"title": "Notes", "file": file}, format="multipart"
    )

    response = authed_client.get("/api/v1/dashboard/me/")

    assert response.status_code == 200
    assert response.data["total_projects"] == 1
    assert len(response.data["activity_last_14_days"]) == 14
    # today should show at least the register + upload + dashboard calls
    assert response.data["activity_last_14_days"][-1]["count"] > 0


@pytest.mark.django_db
def test_user_dashboard_counts_downloads(authed_client):
    file = SimpleUploadedFile("notes.pdf", b"content", content_type="application/pdf")
    upload = authed_client.post(
        "/api/v1/projects/upload/", {"title": "Notes", "file": file}, format="multipart"
    )
    project_id = upload.data["id"]

    authed_client.get(f"/api/v1/projects/{project_id}/download/")
    authed_client.get(f"/api/v1/projects/{project_id}/download/")

    response = authed_client.get("/api/v1/dashboard/me/")
    assert response.data["total_downloads"] == 2


@pytest.mark.django_db
def test_admin_dashboard_requires_staff(authed_client):
    response = authed_client.get("/api/v1/dashboard/admin/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_admin_dashboard_visible_to_staff(authed_client, django_user_model):
    user = django_user_model.objects.get(id=authed_client.user_id)
    user.is_staff = True
    user.save(update_fields=["is_staff"])

    response = authed_client.get("/api/v1/dashboard/admin/")

    assert response.status_code == 200
    assert response.data["total_users"] >= 1
    assert "most_active_users" in response.data
