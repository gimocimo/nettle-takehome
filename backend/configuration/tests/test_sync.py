import shutil

import pytest
from django.conf import settings

from configuration.sync import ConfigError, apply_config, load_config
from reports.models import ReportTemplate, SectionDefinition
from tenancy.db import tenant_transaction
from tenancy.models import Organization


@pytest.fixture
def config_dir(tmp_path):
    target = tmp_path / "tenant_config"
    shutil.copytree(settings.TENANT_CONFIG_DIR, target)
    return target


def _active_template(org_slug, key):
    return ReportTemplate.objects.get(organization__slug=org_slug, key=key, is_active=True)


def test_repository_config_is_valid():
    """CI guard: a customer config change that doesn't validate never reaches a deploy."""
    load_config(settings.TENANT_CONFIG_DIR)


@pytest.mark.django_db
def test_sync_is_idempotent(config_dir):
    apply_config(load_config(config_dir))
    counts = (SectionDefinition.objects.count(), ReportTemplate.objects.count())
    assert apply_config(load_config(config_dir)).changes == []
    assert (SectionDefinition.objects.count(), ReportTemplate.objects.count()) == counts


@pytest.mark.django_db
def test_changing_a_library_section_versions_it_and_every_template_using_it(config_dir):
    apply_config(load_config(config_dir))
    before = _active_template("customer-a", "property-cope-survey")
    path = config_dir / "library/sections/fire-protection.yaml"
    path.write_text(path.read_text().replace("Overall adequacy of fire protection.", "Overall adequacy."))
    apply_config(load_config(config_dir))

    after = _active_template("customer-a", "property-cope-survey")
    assert after.version == before.version + 1
    assert _active_template("customer-b", "site-safety-review").version == 2
    # The old version is untouched, so reports generated with it render exactly as before.
    before.refresh_from_db()
    assert before.is_active is False
    assert {s.key: s.version for s in before.ordered_sections()}["fire-protection"] == 1
    assert {s.key: s.version for s in after.ordered_sections()}["fire-protection"] == 2


def test_unknown_section_reference_is_rejected(config_dir):
    path = config_dir / "organizations/customer-b.yaml"
    path.write_text(path.read_text().replace("electrical,", "electrical, no-such-section,"))
    with pytest.raises(ConfigError, match="no-such-section"):
        load_config(config_dir)


def test_invalid_question_type_is_rejected(config_dir):
    path = config_dir / "library/sections/electrical.yaml"
    path.write_text(path.read_text().replace("type: long_text", "type: essay", 1))
    with pytest.raises(ConfigError, match="electrical.yaml"):
        load_config(config_dir)


@pytest.mark.django_db
def test_templates_removed_from_config_are_retired_not_deleted(config_dir):
    apply_config(load_config(config_dir))
    path = config_dir / "organizations/default-insurer.yaml"
    text = path.read_text()
    path.write_text(text[: text.index("  - key: property-cope-survey")])
    apply_config(load_config(config_dir))
    template = ReportTemplate.objects.get(organization__slug="default-insurer", key="property-cope-survey")
    assert template.is_active is False


@pytest.mark.django_db
def test_tenants_see_the_shared_library_and_only_their_own_private_sections(config_dir):
    apply_config(load_config(config_dir))
    with tenant_transaction(Organization.objects.get(slug="customer-a")):
        keys = set(SectionDefinition.objects.values_list("key", flat=True))
    assert "fire-protection" in keys
    assert "safety-summary" not in keys  # customer B's own section
