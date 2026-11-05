from django.conf import settings
from django.core.mail import send_mail
from django.tasks import task

from tenancy.db import tenant_transaction
from tenancy.models import Organization

from .models import Notification


class EmailDeliveryError(Exception):
    transient = True  # SMTP hiccups are worth retrying


@task
def send_notification_email(*, organization_id, notification_id):
    organization = Organization.objects.get(pk=organization_id)
    with tenant_transaction(organization):
        notification = Notification.objects.select_related("user").get(pk=notification_id)
    if not notification.user.email:
        return
    link = f"{settings.FRONTEND_URL}{notification.link}" if notification.link else settings.FRONTEND_URL
    try:
        send_mail(
            subject=notification.title,
            message=f"{notification.body}\n\nOpen in Nettle: {link}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[notification.user.email],
        )
    except OSError as exc:
        raise EmailDeliveryError(str(exc)) from exc
