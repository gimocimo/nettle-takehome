import json

import httpx
import pytest
from django.core.management import call_command

from jobs.models import Job
from nettle_core.testing import drain_jobs, make_member, make_org, org_url
from tenancy.models import Membership, Organization
from webhooks.events import emit
from webhooks.models import WebhookDelivery, WebhookEndpoint
from webhooks.signing import sign, verify_signature
from webhooks.ssrf import UnsafeWebhookURL, check_url


def test_signatures_verify_and_detect_tampering_and_replays():
    body = b'{"event":"report.completed"}'
    header = sign("whsec_test", body, timestamp=1_000_000)
    assert verify_signature("whsec_test", header, body, now=1_000_100)
    assert not verify_signature("whsec_test", header, body + b" ", now=1_000_100)  # tampered
    assert not verify_signature("other-secret", header, body, now=1_000_100)
    assert not verify_signature("whsec_test", header, body, now=1_000_000 + 3600)  # replayed later
    assert not verify_signature("whsec_test", "garbage", body)


def test_webhooks_cannot_target_the_internal_network(settings):
    settings.WEBHOOK_ALLOW_PRIVATE_HOSTS = False
    for url in ["http://example.com/hook", "https://127.0.0.1/hook", "https://10.0.0.5/hook", "https://169.254.169.254/latest"]:
        with pytest.raises(UnsafeWebhookURL):
            check_url(url)


class _Response:
    def __init__(self, status_code):
        self.status_code = status_code


@pytest.fixture
def endpoint(db):
    org = make_org()
    return WebhookEndpoint.objects.create(organization=org, url="https://hooks.example.com/nettle", events=["report.completed"])


def test_events_are_signed_and_delivered_through_the_queue(endpoint, monkeypatch):
    sent = []

    def fake_post(url, content, headers, **kwargs):
        sent.append((url, content, headers))
        return _Response(204)

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setattr("webhooks.tasks.check_url", lambda url: None)
    emit(endpoint.organization, "report.completed", {"report_id": "r1"})
    emit(endpoint.organization, "report.failed", {"report_id": "r2"})  # not subscribed
    drain_jobs()

    [(url, body, headers)] = sent
    assert headers["X-Nettle-Event"] == "report.completed"
    assert verify_signature(endpoint.secret, headers["X-Nettle-Signature"], body)
    assert json.loads(body)["data"] == {"report_id": "r1"}
    assert WebhookDelivery.objects.get().status == "succeeded"


def test_failed_deliveries_are_retried(endpoint, monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _Response(503))
    monkeypatch.setattr("webhooks.tasks.check_url", lambda url: None)
    emit(endpoint.organization, "report.completed", {"report_id": "r1"})
    drain_jobs()
    job = Job.objects.get(task_path="webhooks.tasks.deliver_webhook")
    assert job.status == "READY" and job.attempts == 1  # waiting for its retry
    assert WebhookDelivery.objects.get().last_error == "HTTP 503"


@pytest.mark.django_db
def test_webhook_secrets_are_generated_and_only_admins_can_read_them(member_client):
    call_command("sync_config")
    org = Organization.objects.get(slug="default-insurer")
    endpoint = WebhookEndpoint.objects.get(organization=org)
    assert endpoint.secret.startswith("whsec_")
    admin = member_client(org, role=Membership.ADMIN)
    assert admin.get(org_url(org, "webhooks/")).data[0]["secret"] == endpoint.secret
    engineer = member_client(org, role=Membership.ENGINEER)
    assert engineer.get(org_url(org, "webhooks/")).status_code == 403
