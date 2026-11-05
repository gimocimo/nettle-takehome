from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from ai.views import AIBudgetView

# Everything tenant-owned lives under /api/o/<org_slug>/ (see tenancy.api).
# Uploaded files are not served from /media/: see EvidenceViewSet.file.
tenant_patterns = [
    path("portfolio/", include("portfolio.urls")),
    path("assessments/", include("assessments.urls")),
    path("evidence/", include("evidence.urls")),
    path("reports/", include("reports.urls")),
    path("templates/", include("reports.template_urls")),
    path("notifications/", include("notifications.urls")),
    path("webhooks/", include("webhooks.urls")),
    path("ai-budget/", AIBudgetView.as_view()),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("tenancy.auth_urls")),
    path("api/o/<slug:org_slug>/", include(tenant_patterns)),
]

if settings.DEBUG:
    from webhooks.views import dev_webhook_sink

    # Development only: a local webhook receiver that verifies signatures.
    urlpatterns.append(path("api/dev/webhook-sink/", dev_webhook_sink))
