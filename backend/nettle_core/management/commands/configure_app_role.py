import os

from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from tenancy.rls import APP_ROLE


class Command(BaseCommand):
    help = (
        "Let the unprivileged application role log in, with APP_DB_PASSWORD as its "
        "password. Run as the database owner, after migrate (production deploy job)."
    )

    def handle(self, *args, **options):
        password = os.environ.get("APP_DB_PASSWORD", "")
        if len(password) < 16:
            raise CommandError("Set APP_DB_PASSWORD (at least 16 characters).")
        with connection.cursor() as cursor:
            # psycopg2 binds parameters client-side, so this works for ALTER ROLE too.
            cursor.execute(f"ALTER ROLE {APP_ROLE} LOGIN PASSWORD %s", [password])
        self.stdout.write(f"{APP_ROLE} can log in.")
