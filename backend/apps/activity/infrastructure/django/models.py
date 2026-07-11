from django.conf import settings
from django.db import models


class ActivityLog(models.Model):
    """
    One row per tracked user action. Written synchronously from
    ActivityLoggingMiddleware - a single indexed insert is cheap enough
    to do inline; heavier post-processing (e.g. weekly digests) reads
    from this table via Celery in the analytics stage instead of writing
    to it.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="activity_logs", null=True
    )
    action = models.CharField(max_length=64)
    path = models.CharField(max_length=255)
    method = models.CharField(max_length=10)
    status_code = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "activity"
        db_table = "activity_log"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"])]

    def __str__(self) -> str:
        return f"{self.user_id} {self.method} {self.path} ({self.status_code})"
