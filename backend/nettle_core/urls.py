from django.contrib import admin
from django.urls import include, path

# Everything tenant-owned lives under /api/o/<org_slug>/ (see tenancy.api).
# Uploaded files are not served from /media/: see EvidenceViewSet.file.
tenant_patterns = [
    path("portfolio/", include("portfolio.urls")),
    path("assessments/", include("assessments.urls")),
    path("evidence/", include("evidence.urls")),
    path("reports/", include("reports.urls")),
    path("templates/", include("reports.template_urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("tenancy.auth_urls")),
    path("api/o/<slug:org_slug>/", include(tenant_patterns)),
]
