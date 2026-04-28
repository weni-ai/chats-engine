from rest_framework import routers

from chats.apps.api.v2.internal.dashboard.viewsets import InternalDashboardViewsetV2
from chats.apps.api.v2.msgs.viewsets import MessageViewSetV2

router = routers.SimpleRouter()

router.register(r"msg", MessageViewSetV2, basename="message-v2")
router.register(
    "internal/dashboard",
    InternalDashboardViewsetV2,
    basename="dash_internal-v2",
)
