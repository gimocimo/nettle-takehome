from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from configuration.sync import ConfigError, apply_config, load_config


class Command(BaseCommand):
    help = "Validate and apply the configuration-as-code files (section library, organizations)."

    def add_arguments(self, parser):
        parser.add_argument("--check", action="store_true", help="Validate only; change nothing.")

    def handle(self, *args, **options):
        try:
            config = load_config(settings.TENANT_CONFIG_DIR)
        except ConfigError as exc:
            raise CommandError(str(exc)) from exc
        if options["check"]:
            self.stdout.write(self.style.SUCCESS("Configuration is valid."))
            return
        # Runs without a tenant context: applying configuration is a privileged operation.
        report = apply_config(config)
        for change in report.changes:
            self.stdout.write(f"  {change}")
        self.stdout.write(self.style.SUCCESS(f"Configuration applied ({len(report.changes)} changes)."))
