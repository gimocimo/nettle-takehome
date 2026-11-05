import pytest

from assessments.models import Assessment
from nettle_core.testing import make_client, make_org, org_url
from tenancy.models import Membership


@pytest.mark.django_db
def test_non_members_get_404_not_403(member_client, org):
    outsider = member_client(make_org("other"))
    assert outsider.get(org_url(org, "portfolio/clients/")).status_code == 404


@pytest.mark.django_db
def test_viewers_can_read_but_not_write(member_client, org):
    viewer = member_client(org, role=Membership.VIEWER)
    client = make_client(org)
    assert viewer.get(org_url(org, "assessments/")).status_code == 200
    response = viewer.post(
        org_url(org, "assessments/"), {"title": "Survey", "client": str(client.id)}, format="json"
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_creates_are_stamped_with_the_url_organization(engineer, org):
    client = make_client(org)
    response = engineer.post(
        org_url(org, "assessments/"), {"title": "Survey", "client": str(client.id)}, format="json"
    )
    assert response.status_code == 201, response.data
    assert Assessment.objects.get(id=response.data["id"]).organization == org


@pytest.mark.django_db
def test_another_organizations_client_does_not_exist_for_us(engineer, org):
    foreign_client = make_client(make_org("other"))
    response = engineer.post(
        org_url(org, "assessments/"), {"title": "Survey", "client": str(foreign_client.id)}, format="json"
    )
    assert response.status_code == 400
    assert "does not exist" in str(response.data["client"])


@pytest.mark.django_db
def test_lists_only_contain_the_url_organizations_rows(engineer, org):
    make_client(org, name="Ours")
    make_client(make_org("other"), name="Theirs")
    names = [c["name"] for c in engineer.get(org_url(org, "portfolio/clients/")).data]
    assert names == ["Ours"]
