import logging
from queue import Queue

from chats.apps.rooms.models import Room

logger = logging.getLogger(__name__)


class QueueRouterService:
    """
    Service to route rooms to available agents.
    """

    def __init__(self, queue: Queue):
        self.queue = queue

    def route_rooms(self):
        """
        Route rooms to available agents.
        """
        logger.info("Start routing rooms for queue %s", self.queue.id)

        rooms = Room.objects.filter(queue=self.queue).order_by("created_on")

        if not rooms.exists():
            logger.info("No rooms to route for queue %s", self.queue.id)
            return

        available_agents = self.queue.available_agents.all()
        available_agents_count = available_agents.count()

        logger.info(
            "Available agents count: %s for queue %s",
            available_agents_count,
            self.queue.id,
        )

        if available_agents_count == 0:
            logger.info("No available agents for queue %s", self.queue.id)
            return

        rooms_to_route = rooms[:available_agents_count]

        available_agents = list(available_agents)

        for room in rooms_to_route:
            agent = available_agents.pop(0)

            room.user = agent
            room.save()

        logger.info("%s rooms routed for queue %s", len(rooms_to_route), self.queue.id)
