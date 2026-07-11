import pytest


@pytest.mark.django_db
def test_authenticated_requests_are_logged(authed_client):
    authed_client.get("/api/v1/notifications/")

    response = authed_client.get("/api/v1/activity/me/")

    assert response.status_code == 200
    actions = [entry["action"] for entry in response.data]
    assert "api_request" in actions or any("notification" in a for a in actions)
