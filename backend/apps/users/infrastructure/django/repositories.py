from __future__ import annotations

import re
from uuid import UUID

from django.contrib.auth.hashers import make_password
from django.db import IntegrityError

from apps.users.domain.entities import UserEntity
from apps.users.domain.ports import UserRepository
from apps.users.infrastructure.django.models import User


class DjangoUserRepository(UserRepository):
    """Translates between the User ORM model and the framework-free UserEntity."""

    def create(self, *, email: str, username: str, password: str) -> UserEntity:
        try:
            user = User.objects.create(
                email=email.lower(),
                username=username,
                password=make_password(password),
            )
        except IntegrityError as exc:
            raise ValueError("email or username already taken") from exc
        return self._to_entity(user)

    def get_by_id(self, user_id: UUID) -> UserEntity | None:
        user = User.objects.filter(id=user_id).first()
        return self._to_entity(user) if user else None

    def get_by_email(self, email: str) -> UserEntity | None:
        user = User.objects.filter(email__iexact=email).first()
        return self._to_entity(user) if user else None

    def exists_with_email_or_username(self, *, email: str, username: str) -> bool:
        return User.objects.filter(email__iexact=email).exists() or User.objects.filter(
            username__iexact=username
        ).exists()

    def verify_password(self, *, email: str, raw_password: str) -> UserEntity | None:
        user = User.objects.filter(email__iexact=email).first()
        if user is None or not user.check_password(raw_password):
            return None
        return self._to_entity(user)

    def get_or_create_from_google(self, *, email: str, google_sub: str, username_hint: str) -> UserEntity:
        user = User.objects.filter(google_sub=google_sub).first()
        if user:
            return self._to_entity(user)

        user = User.objects.filter(email__iexact=email).first()
        if user:
            user.google_sub = google_sub
            user.save(update_fields=["google_sub"])
            return self._to_entity(user)

        username = self._unique_username_from(username_hint)
        user = User.objects.create(
            email=email.lower(),
            username=username,
            google_sub=google_sub,
            password=make_password(None),  # unusable password, login is Google-only
        )
        return self._to_entity(user)

    def _unique_username_from(self, hint: str) -> str:
        base = re.sub(r"[^a-zA-Z0-9_]", "", hint) or "user"
        candidate = base
        suffix = 0
        while User.objects.filter(username__iexact=candidate).exists():
            suffix += 1
            candidate = f"{base}{suffix}"
        return candidate

    @staticmethod
    def _to_entity(user: User) -> UserEntity:
        return UserEntity(
            id=user.id,
            email=user.email,
            username=user.username,
            is_active=user.is_active,
            is_staff=user.is_staff,
            date_joined=user.date_joined,
            google_sub=user.google_sub,
        )
