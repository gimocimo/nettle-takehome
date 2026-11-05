from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ClientFieldViewSet, ClientViewSet

router = DefaultRouter()
router.register("clients", ClientViewSet)
router.register("client-fields", ClientFieldViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
