from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

from apps.notifications.tasks import create_notification_task


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def send_welcome_email_task(self, user_id):
    from apps.users.infrastructure.django.models import User

    user = User.objects.filter(id=user_id).first()
    if not user:
        return

    try:
        send_mail(
            subject="Welcome to SkillSphere",
            message=f"Hi {user.username}, thanks for joining SkillSphere. Time to ship something.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
    except Exception as exc:
        raise self.retry(exc=exc)

    create_notification_task.delay(
        user_id=str(user.id),
        verb="welcome",
        message="Welcome to SkillSphere! Upload your first project to get started.",
        level="info",
    )
