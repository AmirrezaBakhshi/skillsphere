import hashlib

from celery import shared_task

from apps.notifications.tasks import create_notification_task
from apps.projects.infrastructure.django.models import Project

# Reading in chunks avoids loading a large upload entirely into memory.
_HASH_CHUNK_SIZE = 1024 * 1024


@shared_task(bind=True, max_retries=3, default_retry_delay=15)
def process_uploaded_project_task(self, project_id):
    """
    Stand-in for real post-upload processing (virus scanning, thumbnail
    generation, format conversion, etc. would all plug in here). For now
    it: marks the project "processing", computes a checksum of the
    stored file (proves the file is readable end-to-end and gives a
    stable identifier for future duplicate-detection), then marks it
    "ready" and notifies the owner. Any failure marks it "rejected" and
    sends an error notification instead of silently losing the upload.
    """
    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        return

    Project.objects.filter(id=project_id).update(status="processing")

    try:
        digest = hashlib.sha256()
        with project.file.open("rb") as fh:
            for chunk in iter(lambda: fh.read(_HASH_CHUNK_SIZE), b""):
                digest.update(chunk)
        checksum = digest.hexdigest()
    except Exception as exc:
        Project.objects.filter(id=project_id).update(status="rejected")
        create_notification_task.delay(
            user_id=str(project.owner_id),
            verb="project_processing_failed",
            message=f"We couldn't process '{project.title}' - the file could not be read.",
            level="error",
        )
        raise self.retry(exc=exc)

    Project.objects.filter(id=project_id).update(status="ready")
    create_notification_task.delay(
        user_id=str(project.owner_id),
        verb="project_ready",
        message=f"'{project.title}' finished processing and is ready (checksum {checksum[:12]}...).",
        level="success",
    )

    from apps.search.tasks import index_project_task

    index_project_task.delay(str(project_id))
