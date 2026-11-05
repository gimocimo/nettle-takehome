from .models import Notification
from .tasks import send_notification_email


def notify(*, user, organization, kind, title, body="", link=""):
    """In-app notification plus an email, enqueued in the caller's transaction (so
    the email is sent only if the change it reports was actually committed)."""
    if user is None:
        return None
    notification = Notification.objects.create(
        organization=organization, user=user, kind=kind, title=title, body=body, link=link
    )
    send_notification_email.enqueue(
        organization_id=str(organization.id), notification_id=str(notification.id)
    )
    return notification
