"""Schema of the configuration-as-code files in backend/tenant_config/.

library/sections/*.yaml   Nettle's shared section library (one section per file)
organizations/<slug>.yaml  everything that differs between customers

Customer configuration lives in Git: reviewed in pull requests, validated in CI
(test_repository_config_is_valid), applied by `manage.py sync_config`.
"""
from pydantic import BaseModel, ConfigDict, Field

from reports.definitions import SectionSpec


class OrganizationSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    name: str
    region: str = "eu-west"
    language: str = "en-GB"
    currency: str = Field(default="GBP", pattern=r"^[A-Z]{3}$")


class TemplateConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    name: str
    description: str = ""
    language: str | None = None  # defaults to the organization's language
    sections: list[str] = Field(min_length=1)  # section keys, in display order


class OrganizationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization: OrganizationSettings
    # Sections only this organization uses; a key here shadows the shared library.
    sections: list[SectionSpec] = []
    report_templates: list[TemplateConfig] = []
