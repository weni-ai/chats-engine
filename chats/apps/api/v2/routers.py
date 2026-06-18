from rest_framework import routers

from chats.apps.api.v2.internal.rooms.viewsets import InternalListRoomsViewSetV2
from chats.apps.api.v2.internal.dashboard.viewsets import InternalDashboardViewsetV2
from chats.apps.api.v2.msgs.viewsets import MessageViewSetV2
from chats.apps.api.v2.quickmessages.viewsets import QuickMessageViewSetV2
from chats.apps.api.v2.quickmessages.viewsets import SectorQuickMessageViewSetV2

router = routers.SimpleRouter()
router.register(r"msg", MessageViewSetV2, basename="message-v2")
router.register(r"quick_messages", QuickMessageViewSetV2, basename="quick-message-v2")
router.register(
    "internal/rooms",
    InternalListRoomsViewSetV2,
    basename="room_internal_v2",
)
router.register(
    "internal/dashboard",
    InternalDashboardViewsetV2,
    basename="dash_internal-v2",
)
router.register(
    r"sector_quick_messages",
    SectorQuickMessageViewSetV2,
    basename="sector-quick-message-v2",
)
