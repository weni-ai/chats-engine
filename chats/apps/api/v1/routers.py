from django.urls import reverse
from rest_framework import routers

from chats.apps.api.v1.accounts.viewsets import LoginViewset
from chats.apps.api.v1.contacts.viewsets import ContactViewset
from chats.apps.api.v1.msgs.viewsets import MessageViewset
from chats.apps.api.v1.projects.viewsets import ProjectViewset
from chats.apps.api.v1.quickmessages.viewsets import QuickMessageViewset
from chats.apps.api.v1.rooms.viewsets import RoomViewset
<<<<<<< HEAD
from chats.apps.api.v1.sectorqueue.viewsets import SectorQueueViewset, SectorQueueAuthorizationViewset
from chats.apps.api.v1.sectors.viewsets import (
    SectorAuthorizationViewset,
    SectorTagsViewset,
    SectorViewset,
)
=======
from chats.apps.api.v1.sectors.viewsets import (SectorAuthorizationViewset,
                                                SectorTagsViewset,
                                                SectorViewset)
>>>>>>> f06ab257389ccf2e11011eb3cfc9c75f7d2e6a7e


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
<<<<<<< HEAD
router.register("queue", SectorQueueViewset, basename="queue")
router.register("permission/sector", SectorAuthorizationViewset)
router.register("permission/queue", SectorQueueAuthorizationViewset, basename="queue_auth")
=======
router.register("permission/sector", SectorAuthorizationViewset)
router.register("quick_messages", QuickMessageViewset)
>>>>>>> f06ab257389ccf2e11011eb3cfc9c75f7d2e6a7e
