from django.contrib import admin

from apps.activity.infrastructure.django.models import ActivityLog


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("user", "action", "method", "path", "status_code", "created_at")
    list_filter = ("action", "method", "status_code")
    search_fields = ("path", "user__email")
    ordering = ("-created_at",)
