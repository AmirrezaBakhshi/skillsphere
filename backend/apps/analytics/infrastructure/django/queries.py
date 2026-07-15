from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.activity.infrastructure.django.models import ActivityLog
from apps.analytics.domain.entities import (
    ActiveUser,
    AdminDashboardStats,
    DailyCount,
    UserDashboardStats,
)
from apps.analytics.domain.ports import AnalyticsQueryPort
from apps.notifications.infrastructure.django.models import Notification
from apps.projects.infrastructure.django.models import Project
from apps.users.infrastructure.django.models import User

_TREND_WINDOW_DAYS = 14


def _daily_counts(queryset, date_field: str = "created_at") -> list[DailyCount]:
    """
    Turns any queryset with a datetime field into a day-by-day count for
    the trailing _TREND_WINDOW_DAYS, filling in zero for days with no
    rows so charts don't show gaps.
    """
    since = timezone.now() - timedelta(days=_TREND_WINDOW_DAYS)
    rows = (
        queryset.filter(**{f"{date_field}__gte": since})
        .annotate(day=TruncDate(date_field))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )
    counts_by_day = {row["day"].isoformat(): row["count"] for row in rows}

    result = []
    for i in range(_TREND_WINDOW_DAYS - 1, -1, -1):
        day = (timezone.now() - timedelta(days=i)).date().isoformat()
        result.append(DailyCount(date=day, count=counts_by_day.get(day, 0)))
    return result


class DjangoAnalyticsQueries(AnalyticsQueryPort):
    def get_user_dashboard(self, user_id: UUID) -> UserDashboardStats:
        projects = Project.objects.filter(owner_id=user_id)
        status_counts = dict(
            projects.values_list("status").annotate(count=Count("id")).order_by()
        )
        total_downloads = projects.aggregate(total=Sum("download_count"))["total"] or 0
        unread_notifications = Notification.objects.filter(
            user_id=user_id, is_read=False
        ).count()
        activity = _daily_counts(ActivityLog.objects.filter(user_id=user_id))

        return UserDashboardStats(
            total_projects=projects.count(),
            projects_ready=status_counts.get("ready", 0),
            projects_processing=status_counts.get("processing", 0)
            + status_counts.get("pending", 0),
            projects_rejected=status_counts.get("rejected", 0),
            total_downloads=total_downloads,
            unread_notifications=unread_notifications,
            activity_last_14_days=activity,
        )

    def get_admin_dashboard(self) -> AdminDashboardStats:
        projects = Project.objects.all()
        status_counts = dict(
            projects.values_list("status").annotate(count=Count("id")).order_by()
        )
        total_downloads = projects.aggregate(total=Sum("download_count"))["total"] or 0

        top_users = (
            ActivityLog.objects.exclude(user_id=None)
            .values("user__username")
            .annotate(action_count=Count("id"))
            .order_by("-action_count")[:5]
        )

        return AdminDashboardStats(
            total_users=User.objects.count(),
            total_projects=projects.count(),
            total_downloads=total_downloads,
            projects_by_status=status_counts,
            signups_last_14_days=_daily_counts(User.objects.all(), date_field="date_joined"),
            requests_last_14_days=_daily_counts(ActivityLog.objects.all()),
            most_active_users=[
                ActiveUser(username=row["user__username"], action_count=row["action_count"])
                for row in top_users
            ],
        )
