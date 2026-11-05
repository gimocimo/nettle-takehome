import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from tenancy.models import Membership, Organization


@pytest.mark.django_db
def test_a_user_has_at_most_one_membership_per_organization():
    user = get_user_model().objects.create_user("eng@example.test", password="x")
    org = Organization.objects.create(slug="acme", name="Acme Insurance")
    Membership.objects.create(user=user, organization=org, role=Membership.ENGINEER)
    with pytest.raises(IntegrityError):
        Membership.objects.create(user=user, organization=org, role=Membership.ADMIN)


@pytest.mark.django_db
def test_a_user_can_belong_to_several_organizations():
    user = get_user_model().objects.create_user("consultant@example.test", password="x")
    for slug in ("acme", "globex"):
        org = Organization.objects.create(slug=slug, name=slug.title())
        Membership.objects.create(user=user, organization=org, role=Membership.VIEWER)
    assert user.memberships.count() == 2
