from django.urls import path, include
from rest_framework import routers

from chats.apps.api.v2.external.rooms.views import ExternalRoomMetricsViewSet


router = routers.SimpleRouter()

router.register(
    "rooms_metrics",
    ExternalRoomMetricsViewSet,
    basename="external_rooms_metrics_v2",
)


urlpatterns = [
    path("", include(router.urls)),
]
