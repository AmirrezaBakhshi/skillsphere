from django.contrib import admin

from apps.projects.infrastructure.django.models import Project, Tag


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "status", "content_type", "file_size", "download_count", "created_at")
    list_filter = ("status", "content_type")
    search_fields = ("title", "owner__email")
    ordering = ("-created_at",)
    filter_horizontal = ("tags",)
