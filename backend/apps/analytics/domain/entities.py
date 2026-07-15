from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DailyCount:
    """One point on a time-series chart: how many of something happened on a given day."""

    date: str  # ISO date string, e.g. "2026-07-01"
    count: int


@dataclass
class UserDashboardStats:
    total_projects: int
    projects_ready: int
    projects_processing: int
    projects_rejected: int
    total_downloads: int
    unread_notifications: int
    activity_last_14_days: list[DailyCount] = field(default_factory=list)


@dataclass
class ActiveUser:
    username: str
    action_count: int


@dataclass
class AdminDashboardStats:
    total_users: int
    total_projects: int
    total_downloads: int
    projects_by_status: dict[str, int]
    signups_last_14_days: list[DailyCount] = field(default_factory=list)
    requests_last_14_days: list[DailyCount] = field(default_factory=list)
    most_active_users: list[ActiveUser] = field(default_factory=list)
