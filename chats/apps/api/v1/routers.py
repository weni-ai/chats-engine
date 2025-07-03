from rest_framework import routers

from chats.apps.api.v1.accounts.viewsets import LoginViewset, UserDataViewset
from chats.apps.api.v1.contacts.viewsets import ContactViewset
from chats.apps.api.v1.dashboard.viewsets import DashboardLiveViewset
from chats.apps.api.v1.external.agents.viewsets import AgentFlowViewset
from chats.apps.api.v1.external.msgs.viewsets import MessageFlowViewset
from chats.apps.api.v1.external.queues.viewsets import QueueFlowViewset
from chats.apps.api.v1.external.rooms.viewsets import (
    CustomFieldsUserExternalViewSet,
    ExternalListRoomsViewSet,
    ExternalListWithPaginationRoomsViewSet,
    RoomFlowViewSet,
    RoomMetricsViewSet,
    RoomUserExternalViewSet,
)
from chats.apps.api.v1.external.sectors.viewsets import SectorFlowViewset
from chats.apps.api.v1.groups_sectors.viewsets import (
    GroupSectorAuthorizationViewset,
    GroupSectorViewset,
)
from chats.apps.api.v1.internal.dashboard.viewsets import InternalDashboardViewset
from chats.apps.api.v1.internal.projects import viewsets as project_internal_views
from chats.apps.api.v1.internal.rooms.viewsets import InternalListRoomsViewSet
from chats.apps.api.v1.internal.users import viewsets as user_internal_views
from chats.apps.api.v1.msgs.viewsets import MessageMediaViewset, MessageViewset
from chats.apps.api.v1.orgs.viewsets import OrgProjectViewSet
from chats.apps.api.v1.projects.viewsets import (
    CustomStatusTypeViewSet,
    CustomStatusViewSet,
    ProjectPermissionViewset,
    ProjectViewset,
)
from chats.apps.api.v1.queues.viewsets import QueueAuthorizationViewset, QueueViewset
from chats.apps.api.v1.quickmessages.viewsets import (
    QuickMessageViewset,
    SectorQuickMessageViewset,
)
from chats.apps.api.v1.rooms.viewsets import RoomViewset
from chats.apps.api.v1.sectors.viewsets import (
    SectorAuthorizationViewset,
    SectorTagsViewset,
    SectorViewset,
)
from chats.apps.api.v1.users.viewsets import ProfileViewset
from chats.apps.discussions.views import DiscussionViewSet
from chats.apps.history.views import HistoryRoomViewset


class Router(routers.SimpleRouter):
    def get_routes(self, viewset):
        ret = super().get_routes(viewset)
        lookup_field = getattr(viewset, "lookup_field", None)

        if lookup_field:
            # List route.
            ret.append(
                routers.Route(
                    url=r"^{prefix}{trailing_slash}$",
                    mapping={"get": "list", "post": "create"},
                    name="{basename}-list",
                    detail=False,
                    initkwargs={"suffix": "List"},
                )
            )

        detail_url_regex = r"^{prefix}/{lookup}{trailing_slash}$"
        if not lookup_field:
            detail_url_regex = r"^{prefix}{trailing_slash}$"
        # Detail route.
        ret.append(
            routers.Route(
                url=detail_url_regex,
                mapping={
                    "get": "retrieve",
                    "put": "update",
                    "patch": "partial_update",
                    "delete": "destroy",
                },
                name="{basename}-detail",
                detail=True,
                initkwargs={"suffix": "Instance"},
            )
        )

        return ret

    def get_lookup_regex(self, viewset, lookup_prefix=""):
        lookup_fields = getattr(viewset, "lookup_fields", None)
        if lookup_fields:
            base_regex = "(?P<{lookup_prefix}{lookup_url_kwarg}>[^/.]+)"
            return "/".join(
                map(
                    lambda x: base_regex.format(
                        lookup_prefix=lookup_prefix, lookup_url_kwarg=x
                    ),
                    lookup_fields,
                )
            )
        return super().get_lookup_regex(viewset, lookup_prefix)


router = Router()
router.register("accounts/login", LoginViewset)
router.register("accounts/profile", ProfileViewset)
router.register("accounts/userdata", UserDataViewset, basename="user_data")
router.register("room", RoomViewset)
router.register("msg", MessageViewset)
router.register("quick_messages", QuickMessageViewset)
router.register(
    "sector_quick_messages", SectorQuickMessageViewset, basename="sector_quick_message"
)
router.register("media", MessageMediaViewset)
router.register("contact", ContactViewset)
router.register("history/rooms", HistoryRoomViewset, basename="history_room")
router.register("discussion", DiscussionViewSet, basename="discussion")
router.register("sector", SectorViewset)
router.register("group_sector", GroupSectorViewset, basename="group_sector")
router.register(
    "authorization/group_sector",
    GroupSectorAuthorizationViewset,
    basename="group_sector_auth",
)
router.register("tag", SectorTagsViewset)
router.register(
    r"org/(?P<org>[\w-]+)/projects", OrgProjectViewSet, basename="org-projects"
)

router.register("project", ProjectViewset)
router.register("custom_status", CustomStatusViewSet)
router.register("custom_status_type", CustomStatusTypeViewSet)
router.register(
    "permission/project", ProjectPermissionViewset, basename="project_permission"
)
router.register("queue", QueueViewset, basename="queue")
router.register(
    "authorization/sector", SectorAuthorizationViewset, basename="sector_auth"
)
router.register("authorization/queue", QueueAuthorizationViewset, basename="queue_auth")
router.register("dashboard", DashboardLiveViewset, basename="dashboard")
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
router.register(
    "internal/dashboard",
    InternalDashboardViewset,
    basename="dash_internal",
)
router.register(
    "internal/rooms",
    InternalListRoomsViewSet,
    basename="room_internal",
)


# External
router.register("external/msgs", MessageFlowViewset, basename="external_message")
router.register("external/rooms", RoomFlowViewSet, basename="external_rooms")
router.register(
    "external/room_agent", RoomUserExternalViewSet, basename="external_roomagent"
)
router.register(
    "external/custom_field",
    CustomFieldsUserExternalViewSet,
    basename="external_custom_field",
)
router.register(
    "external/rooms_metrics",
    RoomMetricsViewSet,
    basename="external_room_metrics",
)
router.register(
    "external/list_rooms",
    ExternalListRoomsViewSet,
    basename="external_room_list",
)
router.register(
    "external/list_rooms_with_pagination",
    ExternalListWithPaginationRoomsViewSet,
    basename="external_room_list_with_pagination",
)
router.register("external/sectors", SectorFlowViewset, basename="external_sector")
router.register("external/queues", QueueFlowViewset, basename="external_queue")
router.register("external/agents", AgentFlowViewset, basename="external_agent")
