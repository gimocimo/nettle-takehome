"""The client field registry.

The Client model keeps its built-in columns (typed: totals across a portfolio
need real numbers), plus a JSON column for each organization's custom fields.
Which fields exist for an organization, what they're called, whether they're
required and how they're grouped is data (ClientFieldDefinition), synced from
tenant_config/organizations/<slug>.yaml. Adding a customer variation never
needs a model change.
"""
from rest_framework import serializers

FIELD_TYPES = ["text", "long_text", "integer", "decimal", "money", "date", "email", "phone", "boolean", "choice"]

GROUPS = [
    ("contact", "Contact"),
    ("company", "Company details"),
    ("location", "Location"),
    ("insurance", "Insurance"),
    ("risk", "Risk profile"),
    ("other", "Other"),
]
GROUP_KEYS = [key for key, _ in GROUPS]

COMPANY_SIZES = ["Small (1-50)", "Medium (51-250)", "Large (251-1000)", "Enterprise (1000+)"]
COMPANY_SIZE_VALUES = ["small", "medium", "large", "enterprise"]
RISK_RATINGS = ["low", "medium", "high", "critical"]

# key, label, type, group, required, show_in_list, choices (value list)
BUILTIN_FIELDS = [
    ("contact_name", "Contact name", "text", "contact", True, False, []),
    ("contact_email", "Contact email", "email", "contact", True, False, []),
    ("contact_phone", "Contact phone", "phone", "contact", False, False, []),
    ("industry", "Industry", "text", "company", True, True, []),
    ("sub_industry", "Sub-industry", "text", "company", True, False, []),
    ("company_size", "Company size", "choice", "company", True, False, COMPANY_SIZE_VALUES),
    ("annual_revenue", "Annual revenue", "money", "company", True, False, []),
    ("employee_count", "Employees", "integer", "company", True, False, []),
    ("year_established", "Year established", "integer", "company", True, False, []),
    ("address_line_1", "Address", "text", "location", True, False, []),
    ("address_line_2", "Address line 2", "text", "location", False, False, []),
    ("city", "City", "text", "location", True, True, []),
    ("state_province", "State / province", "text", "location", True, False, []),
    ("postal_code", "Postal code", "text", "location", True, False, []),
    ("country", "Country", "text", "location", True, True, []),
    ("policy_number", "Policy number", "text", "insurance", False, False, []),
    ("broker_name", "Broker", "text", "insurance", False, False, []),
    ("broker_contact", "Broker contact", "text", "insurance", False, False, []),
    ("coverage_type", "Coverage type", "text", "insurance", True, False, []),
    ("total_insured_value", "Total insured value", "money", "insurance", False, False, []),
    ("previous_claims_count", "Previous claims", "integer", "insurance", False, False, []),
    ("risk_rating", "Risk rating", "choice", "risk", False, True, RISK_RATINGS),
    ("last_assessment_date", "Last assessment date", "date", "risk", False, False, []),
    ("notes", "Notes", "long_text", "other", False, False, []),
]
BUILTIN_KEYS = {field[0] for field in BUILTIN_FIELDS}


def drf_field(definition):
    """A DRF field that validates and represents values of this definition."""
    kwargs = {"required": False, "allow_null": True}
    field_type = definition.field_type
    if field_type in ("text", "phone"):
        return serializers.CharField(max_length=255, allow_blank=True, **kwargs)
    if field_type == "long_text":
        return serializers.CharField(allow_blank=True, **kwargs)
    if field_type == "email":
        return serializers.EmailField(allow_blank=True, **kwargs)
    if field_type == "integer":
        return serializers.IntegerField(**kwargs)
    if field_type in ("decimal", "money"):
        return serializers.DecimalField(max_digits=15, decimal_places=2, **kwargs)
    if field_type == "date":
        return serializers.DateField(**kwargs)
    if field_type == "boolean":
        return serializers.BooleanField(**kwargs)
    return serializers.ChoiceField(choices=definition.choices, allow_blank=True, **kwargs)


def is_empty(value):
    return value is None or value == ""


def enabled_definitions(organization):
    from .models import ClientFieldDefinition

    definitions = list(ClientFieldDefinition.objects.filter(organization=organization, enabled=True))
    return sorted(definitions, key=lambda d: (GROUP_KEYS.index(d.group), d.position))


def client_values(client, definitions):
    """Values of the given fields, from columns or custom JSON, in API representation."""
    values = {}
    for definition in definitions:
        raw = getattr(client, definition.key) if definition.storage == "column" else client.custom_fields.get(definition.key)
        values[definition.key] = None if is_empty(raw) else drf_field(definition).to_representation(raw)
    return values


def client_context_lines(client):
    """Client details for the AI, using the organization's own field labels."""
    definitions = enabled_definitions(client.organization)
    values = client_values(client, definitions)
    lines = [f"Name: {client.name}"]
    for definition in definitions:
        value = values[definition.key]
        if not is_empty(value):
            lines.append(f"{definition.label}: {value}")
    return lines
