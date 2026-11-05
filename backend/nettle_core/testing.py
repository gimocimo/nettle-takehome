"""Small factories for tests. Plain functions keep tests readable without extra dependencies."""
import itertools
from datetime import date

from django.contrib.auth import get_user_model

from assessments.models import Assessment
from evidence.models import Evidence
from portfolio.models import Client
from reports.models import Report
from tenancy.models import Membership, Organization

_sequence = itertools.count(1)


def org_url(organization, path):
    return f"/api/o/{organization.slug}/{path.lstrip('/')}"


def make_org(slug=None, **overrides):
    slug = slug or f"org-{next(_sequence)}"
    return Organization.objects.create(slug=slug, name=overrides.pop("name", slug.title()), **overrides)


def make_user(email=None, password="test-password", **overrides):
    email = email or f"user{next(_sequence)}@example.test"
    return get_user_model().objects.create_user(username=email, email=email, password=password, **overrides)


def make_member(organization, role=Membership.ENGINEER, user=None):
    user = user or make_user()
    Membership.objects.create(user=user, organization=organization, role=role)
    return user


def make_client(organization=None, **overrides):
    fields = {
        "name": "Acme Warehousing",
        "contact_name": "Jo Bloggs",
        "contact_email": "jo@example.com",
        "industry": "Logistics",
        "sub_industry": "Warehousing",
        "company_size": "medium",
        "annual_revenue": "1000000.00",
        "employee_count": 120,
        "year_established": 1999,
        "address_line_1": "1 Dock Road",
        "city": "Leeds",
        "state_province": "West Yorkshire",
        "postal_code": "LS1 1AA",
        "country": "United Kingdom",
        "coverage_type": "Commercial Property",
    }
    fields.update(overrides)
    return Client.objects.create(organization=organization or make_org(), **fields)


def make_assessment(client=None, **overrides):
    fields = {"title": "Annual survey", "assessment_date": date(2026, 1, 15)}
    fields.update(overrides)
    return Assessment.objects.create(client=client or make_client(), **fields)


def make_note(assessment=None, text="Sprinklers present in all areas.", **overrides):
    fields = {"evidence_type": "note", "title": "Observation", "text_content": text}
    fields.update(overrides)
    return Evidence.objects.create(assessment=assessment or make_assessment(), **fields)


def make_report(assessment=None, **overrides):
    return Report.objects.create(assessment=assessment or make_assessment(), **overrides)


def drain_jobs(max_jobs=50):
    """Run queued background jobs that are due, until there are none left."""
    from django.utils import timezone

    from jobs.models import Job
    from jobs.worker import run_worker

    for _ in range(max_jobs):
        if not Job.objects.filter(status="READY", run_after__lte=timezone.now()).exists():
            return
        run_worker(once=True)
