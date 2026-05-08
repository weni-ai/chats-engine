import logging
from typing import TYPE_CHECKING, Optional

from django.conf import settings
from weni.feature_flags.shortcuts import is_feature_active

from chats.apps.queues.usecases.can_agent_receive_room import (
    CanAgentReceiveRoomUseCase,
)
from chats.apps.queues.utils import start_queue_priority_routing

if TYPE_CHECKING:
    from chats.apps.accounts.models import User
    from chats.apps.contacts.models import Contact
    from chats.apps.projects.models.models import FlowStart, Project
    from chats.apps.queues.models import Queue

logger = logging.getLogger(__name__)


class ResolveRoomUserUseCase:
    def __init__(self, queue: "Queue", project: "Project"):
        self.queue = queue
        self.project = project

    def execute(
        self,
        contact: "Contact",
        user: Optional["User"],
        is_created: bool,
        last_flow_start: Optional["FlowStart"] = None,
    ) -> Optional["User"]:
        if last_flow_start:
            if is_created is True or not contact.rooms.filter(
                queue__sector__project=self.project,
                created_on__gt=last_flow_start.created_on,
            ):
                if last_flow_start.permission.status == "ONLINE":
                    return last_flow_start.permission.user

        if not is_created:
            linked_user = contact.get_linked_user(self.project)
            if linked_user is not None and linked_user.is_online:
                return linked_user.user

        if user and self.project.permissions.filter(
            user=user, status="ONLINE"
        ).exists():
            return user

        if self.project.use_queue_priority_routing:
            return self._resolve_queue_priority()

        return self._resolve_general()

    def _resolve_queue_priority(self) -> Optional["User"]:
        current_queue_size = self.queue.rooms.filter(
            is_active=True, user__isnull=True
        ).count()

        if current_queue_size == 0:
            agent = self.queue.get_available_agent()
            if agent is None:
                return None

            if not is_feature_active(
                settings.AGENT_CAPACITY_RECHECK_FEATURE_FLAG_KEY,
                None,
                str(self.project.uuid),
            ):
                return agent

            capacity = CanAgentReceiveRoomUseCase(self.queue).execute(agent)
            if capacity.can_receive:
                return agent

            start_queue_priority_routing(self.queue)
            return None

        logger.info(
            "Calling start_queue_priority_routing for queue %s from"
            " ResolveRoomUserUseCase because the queue is not empty",
            self.queue.uuid,
        )
        start_queue_priority_routing(self.queue)

        return None

    def _resolve_general(self) -> Optional["User"]:
        if self.queue.rooms.filter(is_active=True, user__isnull=True).exists():
            return None

        agent = self.queue.get_available_agent()
        if agent is None:
            return None

        if not is_feature_active(
            settings.AGENT_CAPACITY_RECHECK_FEATURE_FLAG_KEY,
            None,
            str(self.project.uuid),
        ):
            return agent

        capacity = CanAgentReceiveRoomUseCase(self.queue).execute(agent)
        return agent if capacity.can_receive else None
