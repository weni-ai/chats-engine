from rest_framework import routers

from chats.apps.api.v1.accounts.viewsets import LoginViewset
from chats.apps.api.v1.contacts.viewsets import ContactViewset
from chats.apps.api.v1.msgs.viewsets import MessageViewset
from chats.apps.api.v1.projects.viewsets import ProjectViewset
from chats.apps.api.v1.rooms.viewsets import RoomViewset
from chats.apps.api.v1.sectors.viewsets import (SectorPermissionViewset,
                                                SectorViewset)


class Router(routers.SimpleRouter):
    pass


router = Router()
router.register("accounts/login", LoginViewset)
router.register("room", RoomViewset)
router.register("msg", MessageViewset)
router.register("contact", ContactViewset)
router.register("sector", SectorViewset)
router.register("project", ProjectViewset)
router.register("permission/sector", SectorPermissionViewset)
