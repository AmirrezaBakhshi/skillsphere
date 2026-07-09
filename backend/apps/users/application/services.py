from __future__ import annotations

from dataclasses import dataclass

from apps.users.domain.entities import UserEntity
from apps.users.domain.exceptions import InvalidCredentialsError, UserAlreadyExistsError
from apps.users.domain.ports import UserRepository


@dataclass
class RegistrationService:
    """Use case: create a new account from raw credentials."""

    repository: UserRepository

    def register(self, *, email: str, username: str, password: str) -> UserEntity:
        if self.repository.exists_with_email_or_username(email=email, username=username):
            raise UserAlreadyExistsError(f"An account with email={email} or username={username} already exists")
        return self.repository.create(email=email, username=username, password=password)


@dataclass
class AuthenticationService:
    """Use case: verify credentials for a login attempt."""

    repository: UserRepository

    def authenticate(self, *, email: str, password: str) -> UserEntity:
        user = self.repository.verify_password(email=email, raw_password=password)
        if user is None or not user.is_active:
            raise InvalidCredentialsError("Invalid email or password")
        return user


@dataclass
class GoogleAuthenticationService:
    """
    Use case: exchange a verified Google identity for a local account,
    creating one on first login. Token verification with Google itself
    happens in the adapter layer (api/views.py calls into google-auth);
    this service only deals with domain-level "do we know this person".
    """

    repository: UserRepository

    def authenticate_or_register(self, *, email: str, google_sub: str, username_hint: str) -> UserEntity:
        return self.repository.get_or_create_from_google(
            email=email, google_sub=google_sub, username_hint=username_hint
        )
