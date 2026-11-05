import pytest

from jobs.worker import run_worker
from nettle_core.testing import make_member, make_org, org_url
from notifications.models import Notification
from notifications.service import notify
from tenancy.models import Membership


@pytest.mark.django_db
def test_notify_creates_an_in_app_notification_and_emails_it(mailoutbox):
    org = make_org()
    user = make_member(org)
    notify(user=user, organization=org, kind="report_completed", title="Report ready", link="/o/x/reports/1")
    assert Notification.objects.filter(user=user, read_at__isnull=True).count() == 1
    assert mailoutbox == []  # the email is a background job
    run_worker(once=True)
    assert [m.subject for m in mailoutbox] == ["Report ready"]
    assert "http://localhost:3000/o/x/reports/1" in mailoutbox[0].body


@pytest.mark.django_db
def test_users_only_see_their_own_notifications_and_can_mark_them_read(member_client):
    org = make_org()
    viewer = member_client(org, role=Membership.VIEWER)
    me = Membership.objects.get(organization=org).user
    notify(user=me, organization=org, kind="report_completed", title="Mine")
    notify(user=make_member(org), organization=org, kind="report_completed", title="Someone else's")

    inbox = viewer.get(org_url(org, "notifications/")).data
    assert inbox["unread"] == 1
    assert [n["title"] for n in inbox["results"]] == ["Mine"]

    assert viewer.post(org_url(org, f"notifications/{inbox['results'][0]['id']}/read/")).status_code == 200
    assert viewer.get(org_url(org, "notifications/")).data["unread"] == 0


@pytest.mark.django_db
def test_notifications_cannot_be_created_through_the_api(member_client):
    org = make_org()
    client = member_client(org, role=Membership.ADMIN)
    assert client.post(org_url(org, "notifications/"), {"title": "fake"}, format="json").status_code == 405
