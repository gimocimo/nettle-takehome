from django.apps import AppConfig
from django.tasks.signals import task_finished


class ReportsConfig(AppConfig):
    name = "reports"

    def ready(self):
        from .signals import finalize_failed_generation

        task_finished.connect(finalize_failed_generation, dispatch_uid="reports.finalize_failed_generation")
