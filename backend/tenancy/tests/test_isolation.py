"""Cross-organization isolation across every tenant endpoint.

An admin of organization A must not be able to see, change or delete organization
B's objects through any endpoint, nor attach A's new objects to B's parents.
Add new tenant endpoints to ENDPOINTS / REFERENCES.
"""
import pytest

from nettle_core.testing import (
    make_assessment,
    make_client,
    make_note,
    make_org,
    make_report,
    org_url,
)
from tenancy.models import Membership

ENDPOINTS = {
    "clients": ("portfolio/clients/", lambda org: make_client(org)),
    "assessments": ("assessments/", lambda org: make_assessment(make_client(org))),
    "evidence": ("evidence/", lambda org: make_note(make_assessment(make_client(org)))),
    "reports": ("reports/", lambda org: make_report(make_assessment(make_client(org)))),
}

REFERENCES = [
    ("assessments/", "client", lambda org: make_client(org), {"title": "Survey"}),
    ("evidence/", "assessment", lambda org: make_assessment(make_client(org)), {"text_content": "Note"}),
    ("reports/", "assessment", lambda org: make_assessment(make_client(org)), {}),
]


@pytest.fixture
def setup(member_client):
    org_a, org_b = make_org("org-a"), make_org("org-b")
    return org_a, org_b, member_client(org_a, role=Membership.ADMIN)


@pytest.mark.django_db
@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_lists_never_include_other_organizations_rows(setup, endpoint):
    org_a, org_b, alice = setup
    path, make = ENDPOINTS[endpoint]
    ours, theirs = make(org_a), make(org_b)
    ids = {row["id"] for row in alice.get(org_url(org_a, path)).data}
    assert str(ours.id) in ids
    assert str(theirs.id) not in ids


@pytest.mark.django_db
@pytest.mark.parametrize("endpoint", ENDPOINTS)
@pytest.mark.parametrize("method", ["get", "patch", "put", "delete"])
def test_other_organizations_objects_are_not_found(setup, endpoint, method):
    org_a, org_b, alice = setup
    path, make = ENDPOINTS[endpoint]
    theirs = make(org_b)
    for url_org in (org_a, org_b):  # through our URL, and through theirs (not a member)
        response = getattr(alice, method)(org_url(url_org, f"{path}{theirs.id}/"), {}, format="json")
        assert response.status_code == 404, (url_org.slug, response.status_code)
    assert type(theirs).objects.filter(pk=theirs.pk).exists()


@pytest.mark.django_db
@pytest.mark.parametrize("path,field,make_parent,extra", REFERENCES)
def test_new_objects_cannot_reference_another_organizations_parent(setup, path, field, make_parent, extra):
    org_a, org_b, alice = setup
    parent = make_parent(org_b)
    response = alice.post(org_url(org_a, path), {field: str(parent.id), **extra}, format="json")
    assert response.status_code == 400
    assert "does not exist" in str(response.data[field])


@pytest.mark.django_db
def test_report_generation_cannot_target_another_organizations_report(setup):
    org_a, org_b, alice = setup
    theirs = make_report(make_assessment(make_client(org_b)))
    response = alice.post(org_url(org_a, f"reports/{theirs.id}/generate/"))
    assert response.status_code == 404
