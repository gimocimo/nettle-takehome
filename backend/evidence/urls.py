from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EvidenceViewSet

router = DefaultRouter()
router.register("", EvidenceViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
