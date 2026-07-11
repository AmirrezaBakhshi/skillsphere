from django.contrib import admin

from apps.notifications.infrastructure.django.models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "verb", "level", "is_read", "created_at")
    list_filter = ("level", "is_read")
    search_fields = ("verb", "message", "user__email")
    ordering = ("-created_at",)
