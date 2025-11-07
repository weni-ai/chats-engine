from rest_framework import routers

from chats.apps.api.v2.external.rooms.views import ExternalRoomMetricsViewSet


router = routers.SimpleRouter()

router.register(
    "external/rooms",
    ExternalRoomMetricsViewSet,
    basename="external_rooms_metrics_v2",
)
