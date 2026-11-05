from dataclasses import dataclass, field
from pathlib import Path

import yaml
from django.db import transaction
from pydantic import ValidationError

from reports.definitions import SectionSpec, content_hash
from reports.models import ReportTemplate, SectionDefinition, TemplateSection
from tenancy.models import Organization

from .schema import OrganizationConfig


class ConfigError(Exception):
    pass


@dataclass
class LoadedConfig:
    library: list[SectionSpec]
    organizations: list[OrganizationConfig]


@dataclass
class SyncReport:
    changes: list[str] = field(default_factory=list)


def _read_yaml(path: Path):
    try:
        return yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path.name}: invalid YAML: {exc}") from exc


def load_config(config_dir: Path) -> LoadedConfig:
    """Parse and validate every file; nothing touches the database here."""
    library, organizations = [], []
    try:
        for path in sorted((config_dir / "library" / "sections").glob("*.yaml")):
            library.append(SectionSpec.model_validate(_read_yaml(path)))
        for path in sorted((config_dir / "organizations").glob("*.yaml")):
            organizations.append(OrganizationConfig.model_validate(_read_yaml(path)))
    except ValidationError as exc:
        raise ConfigError(f"{path.name}: {exc}") from exc

    library_keys = {section.key for section in library}
    for org in organizations:
        available = library_keys | {section.key for section in org.sections}
        for template in org.report_templates:
            missing = [key for key in template.sections if key not in available]
            if missing:
                raise ConfigError(
                    f"{org.organization.slug}: template '{template.key}' uses unknown sections {missing}"
                )
    return LoadedConfig(library=library, organizations=organizations)


@transaction.atomic
def apply_config(config: LoadedConfig) -> SyncReport:
    """Idempotent: re-applying the same files changes nothing. A changed section or
    template becomes a new immutable version; existing reports keep their version."""
    report = SyncReport()
    shared = {spec.key: _upsert_section(None, spec, report) for spec in config.library}
    for org_config in config.organizations:
        organization = _upsert_organization(org_config, report)
        own = {spec.key: _upsert_section(organization, spec, report) for spec in org_config.sections}
        available = {**shared, **own}
        active_keys = []
        for template in org_config.report_templates:
            _upsert_template(organization, template, [available[k] for k in template.sections], report)
            active_keys.append(template.key)
        removed = ReportTemplate.objects.filter(organization=organization, is_active=True).exclude(
            key__in=active_keys
        )
        for template in removed:
            report.changes.append(f"{organization.slug}: retired template {template.key}")
        removed.update(is_active=False)
    return report


def _upsert_organization(org_config, report):
    settings = org_config.organization
    values = settings.model_dump(exclude={"slug"})
    organization, created = Organization.objects.get_or_create(slug=settings.slug, defaults=values)
    if created:
        report.changes.append(f"{settings.slug}: created organization")
    elif any(getattr(organization, key) != value for key, value in values.items()):
        Organization.objects.filter(pk=organization.pk).update(**values)
        organization.refresh_from_db()
        report.changes.append(f"{settings.slug}: updated organization settings")
    return organization


def _upsert_section(organization, spec, report):
    data = spec.model_dump(mode="json")
    digest = content_hash(data)
    latest = (
        SectionDefinition.objects.filter(organization=organization, key=spec.key)
        .order_by("-version")
        .first()
    )
    if latest and latest.content_hash == digest:
        return latest
    section = SectionDefinition.objects.create(
        organization=organization,
        key=spec.key,
        version=latest.version + 1 if latest else 1,
        title=spec.title,
        definition=data,
        content_hash=digest,
    )
    owner = organization.slug if organization else "library"
    report.changes.append(f"{owner}: section {spec.key} v{section.version}")
    return section


def _upsert_template(organization, template_config, sections, report):
    language = template_config.language or organization.language
    data = {
        "name": template_config.name,
        "description": template_config.description,
        "language": language,
        "sections": [str(section.id) for section in sections],
    }
    digest = content_hash(data)
    versions = ReportTemplate.objects.filter(organization=organization, key=template_config.key)
    latest = versions.order_by("-version").first()
    if latest and latest.content_hash == digest:
        if not latest.is_active:
            latest.is_active = True
            latest.save(update_fields=["is_active"])
        return latest
    versions.filter(is_active=True).update(is_active=False)
    template = ReportTemplate.objects.create(
        organization=organization,
        key=template_config.key,
        version=latest.version + 1 if latest else 1,
        name=template_config.name,
        description=template_config.description,
        language=language,
        content_hash=digest,
    )
    TemplateSection.objects.bulk_create(
        TemplateSection(template=template, section=section, position=position)
        for position, section in enumerate(sections)
    )
    report.changes.append(f"{organization.slug}: template {template.key} v{template.version}")
    return template
