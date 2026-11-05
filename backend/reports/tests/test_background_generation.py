import pytest
from django.core.management import call_command
from django.utils import timezone

from ai.client import LLMError
from ai.testing import FakeLLM
from jobs.models import Job
from jobs.worker import run_worker
from nettle_core.testing import make_assessment, make_client, make_note, make_org, org_url
from reports.models import ReportTemplate
from tenancy.models import Membership, Organization


@pytest.fixture
def env(db, member_client, monkeypatch):
    call_command("sync_config")
    org = Organization.objects.get(slug="default-insurer")
    assessment = make_assessment(make_client(org))
    make_note(assessment, text="Sprinklers present in all areas.")
    template = ReportTemplate.objects.get(organization=org, key="standard-risk-report", is_active=True)
    fake = FakeLLM()
    monkeypatch.setattr("reports.generation.get_client", lambda: fake)

    class Env:
        pass

    env = Env()
    env.org, env.assessment, env.template, env.fake = org, assessment, template, fake
    env.engineer = member_client(org)
    env.member_client = member_client
    env.monkeypatch = monkeypatch
    return env


def _start(env, client=None):
    return (client or env.engineer).post(
        org_url(env.org, "reports/"),
        {"assessment": str(env.assessment.id), "template": str(env.template.id)},
        format="json",
    )


def _report(env, report_id):
    return env.engineer.get(org_url(env.org, f"reports/{report_id}/")).data


def test_starting_a_report_queues_it_and_returns_at_once(env):
    response = _start(env)
    assert response.status_code == 202, response.data
    assert response.data["status"] == "queued"
    assert response.data["progress_total"] == len(env.template.ordered_sections())
    assert env.fake.calls == []  # no AI call inside the request
    assert Job.objects.filter(kwargs__report_id=response.data["id"]).exists()


def test_the_worker_generates_the_report_in_the_background(env):
    report_id = _start(env).data["id"]
    run_worker(once=True)
    report = _report(env, report_id)
    assert report["status"] == "completed"
    assert report["progress_completed"] == report["progress_total"]
    assert all(q["answer"]["status"] == "answered" for s in report["sections"] for q in s["questions"])
    assert report["usage"]["model"] == "claude-opus-5-5"
    assert float(report["usage"]["cost_usd"]) > 0


def test_starting_the_same_report_twice_is_rejected(env):
    assert _start(env).status_code == 202
    assert _start(env).status_code == 409


def test_viewers_cannot_start_a_generation(env):
    viewer = env.member_client(env.org, role=Membership.VIEWER)
    assert _start(env, client=viewer).status_code == 403


def test_another_organizations_template_cannot_be_used(env):
    call_command("sync_config")
    foreign = ReportTemplate.objects.get(organization__slug="customer-b", is_active=True)
    response = env.engineer.post(
        org_url(env.org, "reports/"),
        {"assessment": str(env.assessment.id), "template": str(foreign.id)},
        format="json",
    )
    assert response.status_code == 400


def test_permanent_failures_mark_the_report_failed_with_a_safe_message(env):
    failing = FakeLLM(fail_on_call=1, failure=LLMError("The AI declined to answer this section.", transient=False))
    env.monkeypatch.setattr("reports.generation.get_client", lambda: failing)
    report_id = _start(env).data["id"]
    run_worker(once=True)
    report = _report(env, report_id)
    assert report["status"] == "failed"
    assert report["error_message"] == "The AI declined to answer this section."


def test_transient_failures_are_retried_automatically(env):
    flaky = FakeLLM(fail_on_call=1)
    env.monkeypatch.setattr("reports.generation.get_client", lambda: flaky)
    report_id = _start(env).data["id"]
    run_worker(once=True)
    report = _report(env, report_id)
    assert report["status"] == "queued" and "Retrying" in report["error_message"]

    Job.objects.filter(kwargs__report_id=report_id).update(run_after=timezone.now())
    run_worker(once=True)
    assert _report(env, report_id)["status"] == "completed"


def test_a_failed_report_can_be_retried_and_resumes(env):
    failing = FakeLLM(fail_on_call=3, failure=LLMError("Rejected.", transient=False))
    env.monkeypatch.setattr("reports.generation.get_client", lambda: failing)
    report_id = _start(env).data["id"]
    run_worker(once=True)
    assert _report(env, report_id)["status"] == "failed"

    resumed = FakeLLM()
    env.monkeypatch.setattr("reports.generation.get_client", lambda: resumed)
    assert env.engineer.post(org_url(env.org, f"reports/{report_id}/retry/")).status_code == 202
    run_worker(once=True)
    assert _report(env, report_id)["status"] == "completed"
    assert len(resumed.calls) == env.template.ordered_sections().__len__() - 2


def test_the_template_list_shows_only_this_organizations_active_templates(env):
    keys = {t["key"] for t in env.engineer.get(org_url(env.org, "templates/")).data}
    assert keys == {"standard-risk-report", "property-cope-survey"}
