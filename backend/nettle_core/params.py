import uuid

from rest_framework.exceptions import ValidationError


def uuid_query_param(request, name):
    """Parse an optional UUID query parameter; malformed values are a 400, not a 500."""
    raw = request.query_params.get(name)
    if raw in (None, ""):
        return None
    try:
        return uuid.UUID(raw)
    except ValueError:
        raise ValidationError({name: "Must be a valid UUID."})
