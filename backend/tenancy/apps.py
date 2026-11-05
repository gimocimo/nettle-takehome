from django.apps import AppConfig
from django.core.signals import request_finished


class TenancyConfig(AppConfig):
    name = "tenancy"

    def ready(self):
        from .db import reset_tenant_context

        request_finished.connect(reset_tenant_context, dispatch_uid="tenancy.reset_tenant_context")
