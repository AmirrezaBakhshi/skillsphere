from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

from apps.notifications.application.services import NotifyUserService
from apps.notifications.infrastructure.django.repositories import DjangoNotificationRepository


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def create_notification_task(self, *, user_id, verb: str, message: str, level: str = "info"):
    """
    Creates an in-app notification in the background. Also emails the
    user for "success"/"error" level notifications (e.g. "your upload
    finished processing" or "your upload failed validation") - "info"
    level notifications (e.g. routine activity) stay in-app only, to
    avoid spamming inboxes.
    """
    service = NotifyUserService(repository=DjangoNotificationRepository())
    try:
        entity = service.notify(user_id=user_id, verb=verb, message=message, level=level)
    except Exception as exc:  # DB hiccup, etc. - retry with backoff
        raise self.retry(exc=exc)

    if level in ("success", "error"):
        _send_email_for_notification(user_id=user_id, verb=verb, message=message)

    return entity.id


def _send_email_for_notification(*, user_id, verb: str, message: str) -> None:
    from apps.users.infrastructure.django.models import User

    user = User.objects.filter(id=user_id).first()
    if not user:
        return

    send_mail(
        subject=f"SkillSphere - {verb.replace('_', ' ')}",
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )
