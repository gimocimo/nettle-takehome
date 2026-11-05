from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AssessmentViewSet

router = DefaultRouter()
router.register("", AssessmentViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
