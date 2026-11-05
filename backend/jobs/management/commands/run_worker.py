from django.core.management.base import BaseCommand

from jobs.worker import run_worker


class Command(BaseCommand):
    help = "Run a background job worker (Postgres queue)."

    def add_arguments(self, parser):
        parser.add_argument("--queue", action="append", dest="queues", help="Queue(s) to consume.")

    def handle(self, *args, **options):
        run_worker(queues=options["queues"] or ["default"])
