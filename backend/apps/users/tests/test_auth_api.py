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



@pytest.mark.django_db
def test_refresh_rotates_cookie_and_blacklists_previous_token(client):
    from rest_framework_simplejwt.exceptions import TokenError
    from rest_framework_simplejwt.tokens import RefreshToken

    register_response = client.post(
        "/api/v1/auth/register/",
        {"email": "rotate@example.com", "username": "rotate", "password": "S3curePass!23"},
        format="json",
    )
    old_refresh = register_response.cookies["ss_refresh_token"].value

    response = client.post("/api/v1/auth/refresh/")

    assert response.status_code == 200
    assert response.data["access"]
    assert "ss_refresh_token" in response.cookies
    new_refresh = response.cookies["ss_refresh_token"].value
    assert new_refresh != old_refresh

    # The token presented before rotation must no longer be accepted.
    client.cookies["ss_refresh_token"] = old_refresh
    reused_response = client.post("/api/v1/auth/refresh/")
    assert reused_response.status_code == 401

    with pytest.raises(TokenError):
        RefreshToken(old_refresh)


@pytest.mark.django_db
def test_refresh_replacement_token_can_be_used(client):
    client.post(
        "/api/v1/auth/register/",
        {"email": "next@example.com", "username": "next", "password": "S3curePass!23"},
        format="json",
    )

    first_rotation = client.post("/api/v1/auth/refresh/")
    assert first_rotation.status_code == 200

    second_rotation = client.post("/api/v1/auth/refresh/")
    assert second_rotation.status_code == 200
    assert second_rotation.cookies["ss_refresh_token"].value != (
        first_rotation.cookies["ss_refresh_token"].value
    )


@pytest.mark.django_db
def test_refresh_rejects_malformed_cookie(client):
    client.cookies["ss_refresh_token"] = "not-a-valid-jwt"
    response = client.post("/api/v1/auth/refresh/")
    assert response.status_code == 401
    assert "ss_refresh_token" not in response.cookies


@pytest.mark.django_db
def test_google_login_rejects_inactive_existing_account(client, monkeypatch):
    from apps.users.infrastructure.django.models import User
    from apps.users.infrastructure.django.google_oauth import GoogleProfile

    user = User.objects.create_user(
        email="inactive-google@example.com",
        username="inactive-google",
        password="S3curePass!23",
        is_active=False,
    )
    monkeypatch.setattr(
        "apps.users.api.views.verify_google_id_token",
        lambda token: GoogleProfile(
            sub="google-sub-inactive", email=user.email, email_verified=True
        ),
    )

    response = client.post(
        "/api/v1/auth/google/",
        {"id_token": "test-token"},
        format="json",
    )

    assert response.status_code == 401
    assert "ss_refresh_token" not in response.cookies


@pytest.mark.django_db
def test_google_login_rejects_unverified_email_claim(client, monkeypatch):
    from rest_framework.exceptions import AuthenticationFailed
    from apps.users.infrastructure.django.google_oauth import verify_google_id_token

    monkeypatch.setattr(
        "apps.users.infrastructure.django.google_oauth.google_id_token.verify_oauth2_token",
        lambda *args, **kwargs: {
            "sub": "google-sub-unverified",
            "email": "unverified@example.com",
            "email_verified": False,
        },
    )

    with pytest.raises(AuthenticationFailed):
        verify_google_id_token("test-token")
