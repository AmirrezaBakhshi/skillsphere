import pytest
from rest_framework.test import APIClient


def _register(client, email, username):
    response = client.post(
        "/api/v1/auth/register/",
        {"email": email, "username": username, "password": "S3curePass!23"},
        format="json",
    )
    return response.data["user"]["id"], response.data["access"]


@pytest.fixture
def two_users():
    client_a = APIClient()
    user_a_id, access_a = _register(client_a, "amy@example.com", "amy")
    client_a.credentials(HTTP_AUTHORIZATION=f"Bearer {access_a}")

    client_b = APIClient()
    user_b_id, access_b = _register(client_b, "devon@example.com", "devon")
    client_b.credentials(HTTP_AUTHORIZATION=f"Bearer {access_b}")

    return {"a": (client_a, user_a_id), "b": (client_b, user_b_id)}


@pytest.mark.django_db
def test_start_conversation_creates_and_is_idempotent(two_users):
    client_a, user_a_id = two_users["a"]
    _, user_b_id = two_users["b"]

    first = client_a.post("/api/v1/chat/start/", {"other_user_id": user_b_id}, format="json")
    second = client_a.post("/api/v1/chat/start/", {"other_user_id": user_b_id}, format="json")

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.data["id"] == second.data["id"]


@pytest.mark.django_db
def test_cannot_start_conversation_with_self(two_users):
    client_a, user_a_id = two_users["a"]
    response = client_a.post("/api/v1/chat/start/", {"other_user_id": user_a_id}, format="json")
    assert response.status_code == 400


@pytest.mark.django_db
def test_send_and_list_messages_via_rest_fallback(two_users):
    client_a, _ = two_users["a"]
    client_b, user_b_id = two_users["b"]

    conversation = client_a.post("/api/v1/chat/start/", {"other_user_id": user_b_id}, format="json").data
    conversation_id = conversation["id"]

    client_a.post(f"/api/v1/chat/{conversation_id}/messages/", {"body": "hey!"}, format="json")
    client_b.post(f"/api/v1/chat/{conversation_id}/messages/", {"body": "hi there"}, format="json")

    history = client_a.get(f"/api/v1/chat/{conversation_id}/messages/")

    assert history.status_code == 200
    assert [m["body"] for m in history.data] == ["hey!", "hi there"]


@pytest.mark.django_db
def test_non_participant_cannot_read_or_send(two_users):
    client_a, _ = two_users["a"]
    client_b, user_b_id = two_users["b"]

    conversation = client_a.post("/api/v1/chat/start/", {"other_user_id": user_b_id}, format="json").data
    conversation_id = conversation["id"]

    outsider = APIClient()
    _, access_c = _register(outsider, "theo@example.com", "theo")
    outsider.credentials(HTTP_AUTHORIZATION=f"Bearer {access_c}")

    read = outsider.get(f"/api/v1/chat/{conversation_id}/messages/")
    send = outsider.post(f"/api/v1/chat/{conversation_id}/messages/", {"body": "hi"}, format="json")

    assert read.status_code == 404
    assert send.status_code == 404


@pytest.mark.django_db
def test_empty_message_is_rejected(two_users):
    client_a, _ = two_users["a"]
    client_b, user_b_id = two_users["b"]

    conversation = client_a.post("/api/v1/chat/start/", {"other_user_id": user_b_id}, format="json").data

    response = client_a.post(f"/api/v1/chat/{conversation['id']}/messages/", {"body": "   "}, format="json")
    assert response.status_code == 400


@pytest.mark.django_db
def test_list_my_conversations(two_users):
    client_a, _ = two_users["a"]
    _, user_b_id = two_users["b"]

    client_a.post("/api/v1/chat/start/", {"other_user_id": user_b_id}, format="json")

    response = client_a.get("/api/v1/chat/mine/")
    assert response.status_code == 200
    assert len(response.data) == 1
