from django.urls import reverse
from rest_framework import routers

from chats.apps.api.v1.accounts.viewsets import LoginViewset
from chats.apps.api.v1.contacts.viewsets import ContactViewset
from chats.apps.api.v1.msgs.viewsets import MessageViewset, MessageMediaViewset
from chats.apps.api.v1.projects.viewsets import ProjectViewset, ProjectPermissionViewset
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
from chats.apps.api.v1.internal.users import viewsets as user_internal_views
from chats.apps.api.v1.internal.projects import viewsets as project_internal_views
from chats.apps.api.v1.internal.queues.viewsets import (
    QueueInternalViewset,
    QueueAuthInternalViewset,
)

from chats.apps.api.v1.external.msgs.viewsets import MessageFlowViewset


class Router(routers.SimpleRouter):
    pass


router = Router()
router.register("accounts/login", LoginViewset)
router.register("room", RoomViewset)
router.register("msg", MessageViewset)
router.register("quick_messages", QuickMessageViewset)
router.register("media", MessageMediaViewset)
router.register("contact", ContactViewset)
router.register("sector", SectorViewset)
router.register("tag", SectorTagsViewset)
router.register("project", ProjectViewset)
router.register("permission/project", ProjectPermissionViewset)
router.register("queue", QueueViewset, basename="queue")
router.register(
    "authorization/sector", SectorAuthorizationViewset, basename="sector_auth"
)
router.register("authorization/queue", QueueAuthorizationViewset, basename="queue_auth")

# Internal

router.register(
    "internal/project",
    project_internal_views.ProjectViewset,
    basename="project_internal",
)
router.register(
    "internal/permission/project",
    project_internal_views.ProjectPermissionViewset,
    basename="project_permission_internal",
)

router.register(
    "internal/user",
    user_internal_views.UserViewSet,
    basename="user_internal",
)

# External
router.register("external/msgs", MessageFlowViewset)
