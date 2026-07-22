import pytest
from channels.db import database_sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from rest_framework.test import APIClient

from apps.chat.infrastructure.channels.jwt_auth_middleware import JWTAuthMiddlewareStack
from apps.chat.infrastructure.channels.routing import websocket_urlpatterns

application = JWTAuthMiddlewareStack(URLRouter(websocket_urlpatterns))


def _register_sync(email, username):
    client = APIClient()
    response = client.post(
        "/api/v1/auth/register/",
        {"email": email, "username": username, "password": "S3curePass!23"},
        format="json",
    )
    return response.data["user"]["id"], response.data["access"]


@database_sync_to_async
def _register(email, username):
    return _register_sync(email, username)


@database_sync_to_async
def _start_conversation(access_token, other_user_id):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
    response = client.post("/api/v1/chat/start/", {"other_user_id": other_user_id}, format="json")
    return response.data["id"]


@pytest.mark.django_db(transaction=True)
async def test_two_users_exchange_messages_over_websocket():
    _, access_a = await _register("amy@example.com", "amy")
    user_b_id, access_b = await _register("devon@example.com", "devon")
    conversation_id = await _start_conversation(access_a, user_b_id)

    communicator_a = WebsocketCommunicator(
        application, f"/ws/chat/{conversation_id}/?token={access_a}"
    )
    connected_a, _ = await communicator_a.connect()
    assert connected_a

    communicator_b = WebsocketCommunicator(
        application, f"/ws/chat/{conversation_id}/?token={access_b}"
    )
    connected_b, _ = await communicator_b.connect()
    assert connected_b

    await communicator_a.send_json_to({"body": "hey devon!"})

    response_a = await communicator_a.receive_json_from()
    response_b = await communicator_b.receive_json_from()

    assert response_a["message"]["body"] == "hey devon!"
    assert response_b["message"]["body"] == "hey devon!"
    assert response_a["message"]["sender_username"] == "amy"

    await communicator_a.disconnect()
    await communicator_b.disconnect()


@pytest.mark.django_db(transaction=True)
async def test_non_participant_connection_is_rejected():
    _, access_a = await _register("amy@example.com", "amy")
    user_b_id, access_b = await _register("devon@example.com", "devon")
    _, access_c = await _register("theo@example.com", "theo")
    conversation_id = await _start_conversation(access_a, user_b_id)

    communicator = WebsocketCommunicator(
        application, f"/ws/chat/{conversation_id}/?token={access_c}"
    )
    connected, _ = await communicator.connect()
    assert connected is False


@pytest.mark.django_db(transaction=True)
async def test_missing_token_is_rejected():
    user_a_id, access_a = await _register("amy@example.com", "amy")
    user_b_id, _ = await _register("devon@example.com", "devon")
    conversation_id = await _start_conversation(access_a, user_b_id)

    communicator = WebsocketCommunicator(application, f"/ws/chat/{conversation_id}/")
    connected, _ = await communicator.connect()
    assert connected is False


@pytest.mark.django_db(transaction=True)
async def test_empty_message_returns_error_not_broadcast():
    _, access_a = await _register("amy@example.com", "amy")
    user_b_id, _ = await _register("devon@example.com", "devon")
    conversation_id = await _start_conversation(access_a, user_b_id)

    communicator = WebsocketCommunicator(application, f"/ws/chat/{conversation_id}/?token={access_a}")
    connected, _ = await communicator.connect()
    assert connected

    await communicator.send_json_to({"body": "   "})
    response = await communicator.receive_json_from()

    assert response["type"] == "error"
    await communicator.disconnect()
