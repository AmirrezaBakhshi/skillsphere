import uuid

from django.conf import settings
from django.db import models


def project_upload_path(instance: "Project", filename: str) -> str:
    # Namespaced by owner so listing a user's own media dir is trivial
    # and one user can never collide with / overwrite another's file.
    return f"projects/{instance.owner_id}/{instance.id}/{filename}"


class Project(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("ready", "Ready"),
        ("rejected", "Rejected"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="projects"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    file = models.FileField(upload_to=project_upload_path, max_length=500)
    file_size = models.PositiveIntegerField()
    content_type = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "projects"
        db_table = "projects_project"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.title} ({self.owner_id})"
