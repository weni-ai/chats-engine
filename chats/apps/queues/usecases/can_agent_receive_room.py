import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from chats.apps.accounts.models import User
    from chats.apps.queues.models import Queue

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AgentCapacityResult:
    can_receive: bool
    active_rooms_count: int
    limit: int

    @property
    def reason(self) -> Optional[str]:
        if self.can_receive:
            return None
        return (
            f"agent has {self.active_rooms_count} active rooms in the sector, "
            f"which reached the limit of {self.limit}"
        )


class CanAgentReceiveRoomUseCase:
    """
    Last-moment verification, performed right before assigning a room to an
    agent, that the agent is still under the sector's rooms limit.

    Closes a race condition between Queue.available_agents / get_available_agent()
    and Room.save() that actually materializes the assignment, where concurrent
    assignments could push an agent above the sector's rooms limit.

    Counting semantics mirror Queue.available_agents:
    - Scope: active rooms in the same sector as the queue.
    - Limit: queue.limit (GroupSector.rooms_limit or Sector.rooms_limit).
    """

    def __init__(self, queue: "Queue"):
        self.queue = queue

    def execute(self, agent: "User") -> AgentCapacityResult:
        from chats.apps.rooms.models import Room

        limit = self.queue.limit

        active_rooms_count = Room.objects.filter(
            user=agent,
            queue__sector=self.queue.sector,
            is_active=True,
        ).count()

        result = AgentCapacityResult(
            can_receive=active_rooms_count < limit,
            active_rooms_count=active_rooms_count,
            limit=limit,
        )

        if not result.can_receive:
            logger.info(
                "Agent %s blocked by capacity recheck on queue %s: %s",
                agent.email,
                self.queue.uuid,
                result.reason,
            )

        return result
