from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class UserEntity:
    """
    Plain domain representation of a user, deliberately kept free of any
    Django or DRF imports. Application services operate on this, never on
    the ORM model directly.
    """

    id: UUID | None
    email: str
    username: str
    is_active: bool = True
    is_staff: bool = False
    date_joined: datetime | None = None
    google_sub: str | None = field(default=None, repr=False)

    def matches_login(self, identifier: str) -> bool:
        return identifier.lower() in {self.email.lower(), self.username.lower()}
