from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/portfolio/", include("portfolio.urls")),
    path("api/assessments/", include("assessments.urls")),
    path("api/evidence/", include("evidence.urls")),
    path("api/reports/", include("reports.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
