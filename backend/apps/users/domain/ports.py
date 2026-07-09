from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from apps.users.domain.entities import UserEntity


class UserRepository(ABC):
    """
    Port describing everything the application layer needs from user
    persistence. The Django adapter (infrastructure/django/repositories.py)
    is one possible implementation; a test double is another.
    """

    @abstractmethod
    def create(self, *, email: str, username: str, password: str) -> UserEntity:
        ...

    @abstractmethod
    def get_by_id(self, user_id: UUID) -> UserEntity | None:
        ...

    @abstractmethod
    def get_by_email(self, email: str) -> UserEntity | None:
        ...

    @abstractmethod
    def exists_with_email_or_username(self, *, email: str, username: str) -> bool:
        ...

    @abstractmethod
    def verify_password(self, *, email: str, raw_password: str) -> UserEntity | None:
        ...

    @abstractmethod
    def get_or_create_from_google(self, *, email: str, google_sub: str, username_hint: str) -> UserEntity:
        ...
