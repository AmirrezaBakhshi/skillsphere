import pytest


@pytest.mark.django_db
def test_registration_creates_a_welcome_notification(authed_client):
    response = authed_client.get("/api/v1/notifications/")

    assert response.status_code == 200
    verbs = [n["verb"] for n in response.data]
    assert "welcome" in verbs


@pytest.mark.django_db
def test_mark_notification_read(authed_client):
    notifications = authed_client.get("/api/v1/notifications/").data
    notification_id = notifications[0]["id"]

    response = authed_client.post(f"/api/v1/notifications/{notification_id}/read/")

    assert response.status_code == 200
    assert response.data["is_read"] is True


@pytest.mark.django_db
def test_marking_someone_elses_notification_404s(authed_client):
    response = authed_client.post("/api/v1/notifications/999999/read/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_unread_filter(authed_client):
    notifications = authed_client.get("/api/v1/notifications/").data
    authed_client.post(f"/api/v1/notifications/{notifications[0]['id']}/read/")

    response = authed_client.get("/api/v1/notifications/?unread=true")
    assert all(not n["is_read"] for n in response.data)
