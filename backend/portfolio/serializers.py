"""Clients are read and written as {name, values}: the values map holds every field
the organization has enabled, whatever its storage (built-in column or custom
JSON). Validation follows the organization's field configuration."""
from rest_framework import serializers

from .fields import GROUPS, client_values, drf_field, enabled_definitions, is_empty
from .models import Client, ClientFieldDefinition


class _OrganizationFieldsMixin:
    def definitions(self):
        if not hasattr(self, "_definitions"):
            self._definitions = enabled_definitions(self.context["organization"])
        return self._definitions


class ClientSerializer(_OrganizationFieldsMixin, serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(max_length=255)
    values = serializers.DictField(required=False)

    def to_representation(self, client):
        definitions = self.definitions()
        values = client_values(client, definitions)
        return {
            "id": str(client.id),
            "name": client.name,
            "values": values,
            # Required by the current configuration but empty (e.g. made required later).
            "incomplete": [d.key for d in definitions if d.required and is_empty(values[d.key])],
            "created_at": client.created_at,
            "updated_at": client.updated_at,
        }

    def validate_values(self, values):
        definitions = {d.key: d for d in self.definitions()}
        cleaned, errors = {}, {}
        for key, raw in values.items():
            definition = definitions.get(key)
            if definition is None:
                errors[key] = ["Unknown field for this organization."]
            elif is_empty(raw):
                cleaned[key] = None
            else:
                try:
                    cleaned[key] = drf_field(definition).run_validation(raw)
                except serializers.ValidationError as exc:
                    errors[key] = exc.detail
        if errors:
            raise serializers.ValidationError(errors)
        return cleaned

    def validate(self, attrs):
        values = attrs.get("values", {})
        missing = []
        for definition in self.definitions():
            if not definition.required:
                continue
            creating = self.instance is None
            if (creating and is_empty(values.get(definition.key))) or (
                not creating and definition.key in values and is_empty(values[definition.key])
            ):
                missing.append(definition.key)
        if missing:
            raise serializers.ValidationError({"values": {key: ["This field is required."] for key in missing}})
        return attrs

    def create(self, validated_data):
        client = Client(organization=self.context["organization"], name=validated_data["name"])
        self._apply(client, validated_data.get("values", {}))
        client.save()
        return client

    def update(self, client, validated_data):
        client.name = validated_data.get("name", client.name)
        self._apply(client, validated_data.get("values", {}))
        client.save()
        return client

    def _apply(self, client, values):
        definitions = {d.key: d for d in self.definitions()}
        for key, value in values.items():
            definition = definitions[key]
            if definition.storage == "column":
                if value is None and not Client._meta.get_field(key).null:
                    value = ""
                setattr(client, key, value)
            else:
                client.custom_fields[key] = None if value is None else drf_field(definition).to_representation(value)


class ClientListSerializer(_OrganizationFieldsMixin, serializers.Serializer):
    def to_representation(self, client):
        listed = [d for d in self.definitions() if d.show_in_list]
        return {"id": str(client.id), "name": client.name, "values": client_values(client, listed), "created_at": client.created_at}


class ClientFieldDefinitionSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source="field_type")

    class Meta:
        model = ClientFieldDefinition
        fields = ["key", "label", "type", "group", "required", "choices", "help_text", "show_in_list"]


GROUP_LABELS = dict(GROUPS)
