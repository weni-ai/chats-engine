from django.urls import reverse
from rest_framework import routers

from chats.apps.api.v1.accounts.viewsets import LoginViewset
from chats.apps.api.v1.contacts.viewsets import ContactViewset
from chats.apps.api.v1.msgs.viewsets import MessageViewset, MessageMediaViewset
from chats.apps.api.v1.projects.viewsets import ProjectViewset
from chats.apps.api.v1.queues.viewsets import (
    QueueAuthorizationViewset,
    QueueViewset,
)
from chats.apps.api.v1.quickmessages.viewsets import QuickMessageViewset
from chats.apps.api.v1.rooms.viewsets import RoomViewset
from chats.apps.api.v1.sectors.viewsets import (
    SectorAuthorizationViewset,
    SectorTagsViewset,
    SectorViewset,
)
from chats.apps.api.v1.internal.sectors import viewsets as sector_internal_views
from chats.apps.api.v1.internal.projects import viewsets as project_internal_views
from chats.apps.api.v1.internal.queues.viewsets import (
    QueueInternalViewset,
    QueueAuthInternalViewset,
)


class Router(routers.SimpleRouter):
    pass


router = Router()
router.register("accounts/login", LoginViewset)
router.register("room", RoomViewset)
router.register("msg", MessageViewset)
router.register("media", MessageMediaViewset)
router.register("contact", ContactViewset)
router.register("sector", SectorViewset)
router.register("tag", SectorTagsViewset)
router.register("project", ProjectViewset)
router.register("queue", QueueViewset, basename="queue")
router.register("permission/sector", SectorAuthorizationViewset)
router.register("permission/queue", QueueAuthorizationViewset, basename="queue_auth")
router.register("permission/sector", SectorAuthorizationViewset)
router.register("quick_messages", QuickMessageViewset)
router.register("internal/queue", QueueInternalViewset, basename="queue_internal")
router.register(
    "internal/sector",
    sector_internal_views.SectorInternalViewset,
    basename="sector_internal",
)
router.register(
    "internal/project",
    project_internal_views.ProjectViewset,
    basename="project_internal",
)
router.register(
    "internal/permission/project",
    project_internal_views.ProjectAuthorizationViewset,
    basename="project_auth_internal",
)
router.register(
    "internal/permissions/sector", sector_internal_views.SectorAuthorizationViewset
)
router.register(
    "internal/permission/queue",
    QueueAuthInternalViewset,
    basename="queue_auth_internal",
)
