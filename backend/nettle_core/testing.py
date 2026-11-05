"""Small factories for tests. Plain functions keep tests readable without extra dependencies."""
from datetime import date

from assessments.models import Assessment
from evidence.models import Evidence
from portfolio.models import Client
from reports.models import Report


def make_client(**overrides):
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
    return Client.objects.create(**fields)


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
