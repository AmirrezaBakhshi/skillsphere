import pytest
from rest_framework.test import APIClient


@pytest.fixture
def authed_client(db):
    """
    An APIClient already carrying a valid access token for a freshly
    registered user. CELERY_TASK_ALWAYS_EAGER=True (see pytest.ini / CI env)
    makes background tasks run in-process during tests, so no worker or
    broker is needed.
    """
    client = APIClient()
    response = client.post(
        "/api/v1/auth/register/",
        {"email": "amy@example.com", "username": "amy", "password": "S3curePass!23"},
        format="json",
    )
    access = response.data["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    client.user_id = response.data["user"]["id"]
    return client
