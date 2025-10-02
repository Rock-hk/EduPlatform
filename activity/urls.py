from django.urls import path, include
from rest_framework import routers
from .views import ActivityViewSet, NotificationViewSet

router = routers.DefaultRouter()
router.register(r"activities", ActivityViewSet, basename="activity")
router.register(r"notifications", NotificationViewSet, basename="notification")

urlpatterns = [
    path("api/", include(router.urls)),
]
