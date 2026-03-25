import logging
from datetime import timedelta
from typing import TYPE_CHECKING

from django.db.models.functions import Coalesce
from django.utils import timezone

from chats.apps.dashboard.models import RoomMetrics
from chats.apps.dashboard.utils import calculate_last_queue_waiting_time
from chats.apps.queues.models import LAST_SEEN_THRESHOLD_SECONDS

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

    def get_rooms_to_route(self):
        """
        Get rooms to route.
        """
        from chats.apps.rooms.models import Room

        return (
            Room.objects.filter(queue=self.queue, is_active=True, user__isnull=True)
            .annotate(date_field=Coalesce("added_to_queue_at", "created_on"))
            .order_by("date_field")
        )

    def route_rooms(self):
        """
        Route rooms to available agents.
        """
        from chats.apps.projects.models import ProjectPermission
        from chats.apps.queues.utils import create_room_assigned_from_queue_feedback
        from chats.apps.rooms.tasks import update_ticket_assignee_async

        logger.info("Start routing rooms for queue %s", self.queue.uuid)

        rooms = self.get_rooms_to_route()

        if not rooms.exists():
            logger.info(
                "No rooms to route for queue %s, ending routing", self.queue.uuid
            )
            return

        if not self.queue.available_agents.exists():
            logger.info(
                "No available agents for queue %s, ending routing", self.queue.uuid
            )
            return

        rooms_routed = 0

        for room in rooms:
            # Checking if the room was already routed
            # This is to avoid routing the same room multiple times
            # (race condition)
            room.refresh_from_db()

            if room.user:

                logger.info(
                    "Room %s already routed to agent %s, skipping",
                    room.uuid,
                    room.user.email,
                )
                continue

            agent = self.queue.get_available_agent()

            if not agent:
                break

            # Double-check agent is still online before assigning
            # This prevents race condition where agent goes offline between
            # get_available_agent() and save()
            is_still_online_filter = {
                "user": agent,
                "project": self.queue.sector.project,
                "status": ProjectPermission.STATUS_ONLINE,
            }

            # If ping timeout feature is enabled, also verify last_seen
            if self.queue._is_ping_timeout_feature_enabled():
                last_seen_threshold = timezone.now() - timedelta(
                    seconds=LAST_SEEN_THRESHOLD_SECONDS
                )
                is_still_online_filter["last_seen__gte"] = last_seen_threshold

            is_still_online = ProjectPermission.objects.filter(
                **is_still_online_filter
            ).exists()

            if not is_still_online:
                logger.info(
                    "Agent %s is no longer online for room %s, skipping",
                    agent.email,
                    room.uuid,
                )
                continue

            old_user_assigned_at = room.user_assigned_at

            room.user = agent
            room.save()

            room.notify_user("update")
            room.notify_queue("update")

            task = update_ticket_assignee_async.delay(
                room_uuid=str(room.uuid),
                ticket_uuid=room.ticket_uuid,
                user_email=agent.email,
            )

            logger.info(
                "[ROOM] Launched async ticket update task - Room: %s, "
                "Ticket: %s, User: %s, Task ID: %s",
                room.uuid,
                room.ticket_uuid,
                agent.email,
                task.id,
            )

            create_room_assigned_from_queue_feedback(room, agent)

            if (
                not old_user_assigned_at
                and room.queue.sector.is_automatic_message_active
                and room.queue.sector.automatic_message_text
            ):
                room.send_automatic_message()

            rooms_routed += 1

            metrics = RoomMetrics.objects.get_or_create(room=room)[0]
            metrics.waiting_time += calculate_last_queue_waiting_time(room)
            metrics.queued_count += 1
            metrics.save()

        logger.info(
            "%s rooms routed for queue %s, ending routing",
            rooms_routed,
            self.queue.uuid,
        )
