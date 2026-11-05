from io import StringIO

import pytest
from django.core.management import call_command


@pytest.mark.django_db
def test_models_and_migrations_are_in_sync():
    """Migrations are generated in development and committed, never at deploy time."""
    out = StringIO()
    try:
        call_command("makemigrations", "--check", "--dry-run", stdout=out)
    except SystemExit:
        pytest.fail(f"Model changes without a committed migration:\n{out.getvalue()}")
