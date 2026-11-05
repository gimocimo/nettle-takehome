import pytest
from django.core.management import CommandError, call_command

from assessments.models import Assessment
from portfolio.models import Client


@pytest.mark.django_db
def test_seed_refuses_to_run_with_debug_off(settings):
    settings.DEBUG = False
    with pytest.raises(CommandError):
        call_command("seed_data")
    assert not Client.objects.exists()


@pytest.mark.django_db
def test_seed_is_all_or_nothing(settings, monkeypatch):
    settings.DEBUG = True

    def explode(*args, **kwargs):
        raise RuntimeError("simulated failure halfway through the seed")

    monkeypatch.setattr(Assessment.objects, "create", explode)
    with pytest.raises(RuntimeError):
        call_command("seed_data")
    assert not Client.objects.exists()


@pytest.mark.django_db
def test_seed_creates_demo_data_once(settings):
    settings.DEBUG = True
    call_command("seed_data")
    call_command("seed_data")
    assert Client.objects.count() == 3
