from django.urls import reverse
from rest_framework import routers

from chats.apps.api.v1.accounts.viewsets import LoginViewset
from chats.apps.api.v1.contacts.viewsets import ContactViewset
from chats.apps.api.v1.msgs.viewsets import MessageViewset
from chats.apps.api.v1.projects.viewsets import ProjectViewset
from chats.apps.api.v1.quickmessages.viewsets import QuickMessageViewset
from chats.apps.api.v1.rooms.viewsets import RoomViewset
from chats.apps.api.v1.queues.viewsets import SectorQueueViewset, SectorQueueAuthorizationViewset
from chats.apps.api.v1.sectors.viewsets import (
    SectorAuthorizationViewset,
    SectorTagsViewset,
    SectorViewset,
)
from chats.apps.api.internal.queues.viewsets import (
    QueueInternalViewset,
    QueueAuthInternalViewset
)
from chats.apps.api.internal.sector.viewsets import (
    SectorInternalViewset,
)
from chats.apps.api.v1.external.msgs.viewsets import (
    MessageViewset,
)



class Router(routers.SimpleRouter):
    pass


router = Router()
router.register("accounts/login", LoginViewset)
router.register("room", RoomViewset)
router.register("msg", MessageViewset)
router.register("contact", ContactViewset)
router.register("sector", SectorViewset)
router.register("tag", SectorTagsViewset)
router.register("project", ProjectViewset)
router.register("queue", SectorQueueViewset, basename="queue")
router.register("internal/sector", SectorInternalViewset, basename="sector_internal")
router.register("internal/queue", QueueInternalViewset, basename="queue_internal")
router.register("internal/message", MessageViewset, basename="message")
router.register("permission/sector", SectorAuthorizationViewset)
router.register("permission/queue", SectorQueueAuthorizationViewset, basename="queue_auth")
router.register("permission/sector", SectorAuthorizationViewset)
router.register("quick_messages", QuickMessageViewset)
router.register("internal/permission/queue", QueueAuthInternalViewset, basename="queue_auth_internal")
