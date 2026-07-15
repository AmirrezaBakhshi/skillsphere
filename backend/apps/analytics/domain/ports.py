from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from apps.analytics.domain.entities import AdminDashboardStats, UserDashboardStats


class AnalyticsQueryPort(ABC):
    """
    Read-model port for cross-cutting reporting. Unlike the repository
    ports in users/notifications/projects (which each own a single
    table), this one deliberately reads across several bounded contexts
    at once (Project, Notification, ActivityLog, User) - see
    DOCUMENTATION_STAGE3.md for why that's an intentional, common
    exception (a CQRS-style read model) rather than a layering violation.
    """

    @abstractmethod
    def get_user_dashboard(self, user_id: UUID) -> UserDashboardStats:
        ...

    @abstractmethod
    def get_admin_dashboard(self) -> AdminDashboardStats:
        ...
