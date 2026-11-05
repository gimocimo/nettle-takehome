import pytest

from assessments.models import Assessment
from nettle_core.testing import make_assessment, make_client, make_note, make_org


@pytest.mark.django_db
def test_children_inherit_the_organization_of_their_parent():
    org = make_org()
    assessment = make_assessment(client=make_client(organization=org))
    note = make_note(assessment=assessment)
    assert assessment.organization == org
    assert note.organization == org


@pytest.mark.django_db
def test_a_child_cannot_point_to_another_organizations_parent():
    client = make_client(organization=make_org())
    with pytest.raises(ValueError):
        Assessment.objects.create(client=client, organization=make_org(), title="Cross-tenant")
