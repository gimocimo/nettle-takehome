import pytest
from django.core.management import CommandError, call_command

from assessments.models import Assessment
from portfolio.models import Client
from tenancy.models import Membership, Organization


@pytest.fixture
def configured(db):
    call_command("sync_config")


@pytest.mark.django_db
def test_seed_refuses_to_run_with_debug_off(settings, configured):
    settings.DEBUG = False
    with pytest.raises(CommandError):
        call_command("seed_data")
    assert not Client.objects.exists()


@pytest.mark.django_db
def test_seed_needs_the_organizations_from_configuration(settings):
    settings.DEBUG = True
    with pytest.raises(CommandError, match="sync_config"):
        call_command("seed_data")


@pytest.mark.django_db
def test_seed_is_all_or_nothing(settings, monkeypatch, configured):
    settings.DEBUG = True

    def explode(*args, **kwargs):
        raise RuntimeError("simulated failure halfway through the seed")

    monkeypatch.setattr(Assessment.objects, "create", explode)
    with pytest.raises(RuntimeError):
        call_command("seed_data")
    assert not Membership.objects.exists()
    assert not Client.objects.exists()


@pytest.mark.django_db
def test_seed_populates_the_three_organizations_once(settings, configured):
    settings.DEBUG = True
    call_command("seed_data")
    call_command("seed_data")
    assert Organization.objects.count() == 3
    consultant = Membership.objects.filter(user__email="consultant@nettle.test")
    assert consultant.count() == 3  # one user, several organizations, different roles
    assert set(Client.objects.values_list("organization__slug", flat=True)) == {
        "default-insurer",
        "customer-a",
        "customer-b",
    }
