from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from apps.analytics.domain.entities import AdminDashboardStats, UserDashboardStats
from apps.analytics.domain.ports import AnalyticsQueryPort


@dataclass
class BuildUserDashboardService:
    repository: AnalyticsQueryPort

    def build(self, user_id: UUID) -> UserDashboardStats:
        return self.repository.get_user_dashboard(user_id)


@dataclass
class BuildAdminDashboardService:
    repository: AnalyticsQueryPort

    def build(self) -> AdminDashboardStats:
        return self.repository.get_admin_dashboard()
