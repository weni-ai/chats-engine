import logging
from typing import TYPE_CHECKING


logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from chats.apps.queues.models import Queue


class QueueRouterService:
    """
    Service to route rooms to available agents, to be used when
    the project is configured to use queue priority routing.
    """

    def __init__(self, queue: "Queue"):
        self.queue = queue

        if not self.queue.sector.project.use_queue_priority_routing:
            raise ValueError("Queue priority routing is not enabled for this project")

    def route_rooms(self):
        """
        Route rooms to available agents.
        """
        from chats.apps.rooms.models import Room

        logger.info("Start routing rooms for queue %s", self.queue.uuid)

        rooms = Room.objects.filter(
            queue=self.queue, is_active=True, user__isnull=True
        ).order_by("created_on")

        if not rooms.exists():
            logger.info(
                "No rooms to route for queue %s, ending routing", self.queue.uuid
            )
            return

        available_agents = self.queue.available_agents.all()
        available_agents_count = available_agents.count()

        logger.info(
            "Available agents count: %s for queue %s",
            available_agents_count,
            self.queue.uuid,
        )

        if available_agents_count == 0:
            logger.info(
                "No available agents for queue %s, ending routing", self.queue.uuid
            )
            return

        rooms_to_route = rooms[:available_agents_count]

        for room in rooms_to_route:
            room.user = self.queue.available_agents.first()
            room.save()

        logger.info(
            "%s rooms routed for queue %s, ending routing",
            len(rooms_to_route),
            self.queue.uuid,
        )
