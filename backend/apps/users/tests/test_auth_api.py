import pytest
from rest_framework.test import APIClient


@pytest.fixture
def client():
    return APIClient()


@pytest.mark.django_db
def test_register_creates_user_and_sets_refresh_cookie(client):
    response = client.post(
        "/api/v1/auth/register/",
        {"email": "amy@example.com", "username": "amy", "password": "S3curePass!23"},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["user"]["email"] == "amy@example.com"
    assert "access" in response.data
    assert "ss_refresh_token" in response.cookies


@pytest.mark.django_db
def test_register_rejects_duplicate_email(client):
    payload = {"email": "amy@example.com", "username": "amy", "password": "S3curePass!23"}
    client.post("/api/v1/auth/register/", payload, format="json")

    response = client.post(
        "/api/v1/auth/register/",
        {**payload, "username": "amy2"},
        format="json",
    )

    assert response.status_code == 409


@pytest.mark.django_db
def test_login_with_wrong_password_is_rejected(client):
    client.post(
        "/api/v1/auth/register/",
        {"email": "amy@example.com", "username": "amy", "password": "S3curePass!23"},
        format="json",
    )

    response = client.post(
        "/api/v1/auth/login/",
        {"email": "amy@example.com", "password": "wrong-password"},
        format="json",
    )

    assert response.status_code == 401


@pytest.mark.django_db
def test_me_requires_a_valid_access_token(client):
    register_response = client.post(
        "/api/v1/auth/register/",
        {"email": "amy@example.com", "username": "amy", "password": "S3curePass!23"},
        format="json",
    )
    access = register_response.data["access"]

    unauthenticated = client.get("/api/v1/auth/me/")
    assert unauthenticated.status_code == 401

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    authenticated = client.get("/api/v1/auth/me/")
    assert authenticated.status_code == 200
    assert authenticated.data["email"] == "amy@example.com"


@pytest.mark.django_db
def test_refresh_requires_the_httponly_cookie(client):
    response = client.post("/api/v1/auth/refresh/")
    assert response.status_code == 401
