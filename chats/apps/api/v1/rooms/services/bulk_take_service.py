import logging
import time
from typing import Dict

from django.conf import settings
from django.db.models import QuerySet

from chats.apps.accounts.models import User
from chats.apps.dashboard.models import RoomMetrics
from chats.apps.dashboard.utils import calculate_last_queue_waiting_time
from chats.apps.queues.models import Queue
from chats.apps.queues.utils import start_queue_priority_routing
from chats.apps.rooms.choices import RoomFeedbackMethods
from chats.apps.rooms.models import Room
from chats.apps.rooms.utils import create_transfer_json
from chats.apps.rooms.views import create_room_feedback_message

logger = logging.getLogger(__name__)


class BulkTakeResult:
    """Result object for bulk take operation"""

    def __init__(self):
        self.success_count = 0
        self.failed_count = 0
        self.errors = []
        self.failed_rooms = []

    def add_success(self):
        self.success_count += 1

    def add_failure(self, room_uuid: str, error: str):
        self.failed_count += 1
        self.errors.append(error)
        self.failed_rooms.append(str(room_uuid))

    def to_dict(self) -> Dict:
        return {
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "total_processed": self.success_count + self.failed_count,
            "errors": self.errors[:10] if self.errors else [],
            "failed_rooms": self.failed_rooms[:10] if self.failed_rooms else [],
            "has_more_errors": len(self.errors) > 10,
        }


class BulkTakeService:
    """
    Service for taking multiple queued rooms for a single user.

    Processes rooms in configurable batches (settings.BULK_TAKE_BATCH_SIZE)
    to avoid overwhelming the database and external dependencies.
    Each room is individually assigned to the user, preserving all
    existing business logic (metrics, feedback messages, automatic
    messages, ticket updates, etc.).

    After each successful take, sends WebSocket notifications and
    schedules metrics — matching the individual pick_queue_room
    endpoint behavior. Queue priority routing is triggered once per
    unique queue at the end of each batch.
    """

    def take(
        self,
        rooms: QuerySet[Room],
        user: User,
    ) -> BulkTakeResult:
        result = BulkTakeResult()

        batch_size = getattr(settings, "BULK_TAKE_BATCH_SIZE", 50)

        room_pks = list(rooms.values_list("pk", flat=True))

        if not room_pks:
            logger.warning("[BULK_TAKE] No rooms provided")
            return result

        total = len(room_pks)
        total_batches = (total + batch_size - 1) // batch_size

        logger.info(
            f"[BULK_TAKE] Starting: {total} rooms in {total_batches} "
            f"batch(es) of {batch_size} for user {user.email}"
        )

        start_time = time.perf_counter()

        for batch_index in range(0, total, batch_size):
            batch_pks = room_pks[batch_index:batch_index + batch_size]
            batch = list(
                Room.objects.filter(pk__in=batch_pks).select_related(
                    "queue__sector__project",
                    "queue__sector",
                    "user",
                )
            )
            batch_number = batch_index // batch_size + 1

            logger.info(
                f"[BULK_TAKE] Processing batch {batch_number}/{total_batches} "
                f"({len(batch)} rooms)"
            )

            affected_queue_ids = set()

            for room in batch:
                if room.user is not None:
                    error_msg = f"Room {room.uuid}: already assigned to {room.user.email}"
                    result.add_failure(room.uuid, error_msg)
                    logger.warning(f"[BULK_TAKE] {error_msg}")
                    continue

                try:
                    feedback = create_transfer_json(
                        action="pick",
                        from_=room.queue,
                        to=user,
                        requested_by=user,
                    )

                    room.user = user
                    room.save()
                    room.add_transfer_to_history(feedback)

                    create_room_feedback_message(
                        room,
                        feedback,
                        method=RoomFeedbackMethods.ROOM_TRANSFER,
                        requested_by=user,
                    )

                    result.add_success()

                    if room.queue_id:
                        affected_queue_ids.add(room.queue_id)

                except Exception as e:
                    error_msg = f"Room {room.uuid}: {str(e)}"
                    result.add_failure(room.uuid, error_msg)
                    logger.warning(f"[BULK_TAKE] Failed to take room: {error_msg}")
                    continue

                self._post_take(room)

            for queue_id in affected_queue_ids:
                try:
                    queue = Queue.objects.get(pk=queue_id)
                    start_queue_priority_routing(queue)
                except Exception as e:
                    logger.warning(
                        f"[BULK_TAKE] Failed to start routing for queue "
                        f"{queue_id}: {str(e)}"
                    )

            has_more_batches = batch_index + batch_size < total
            if has_more_batches:
                time.sleep(0.1)

        elapsed = time.perf_counter() - start_time

        logger.info(
            f"[BULK_TAKE] Completed: {result.success_count} succeeded, "
            f"{result.failed_count} failed - {elapsed:.2f}s"
        )

        return result

    def _post_take(self, room: Room):
        """
        Run post-take operations: WS notifications, metrics, automatic message,
        ticket update. Each operation is individually wrapped so one failure
        does not prevent the others from running.
        """
        try:
            room.notify_queue("update")
        except Exception as e:
            logger.warning(
                f"[BULK_TAKE] notify_queue failed for room {room.uuid}: {e}"
            )

        try:
            room.send_automatic_message()
        except Exception as e:
            logger.warning(
                f"[BULK_TAKE] send_automatic_message failed for room {room.uuid}: {e}"
            )

        try:
            room_metric = RoomMetrics.objects.get_or_create(room=room)[0]
            room_metric.waiting_time += calculate_last_queue_waiting_time(room)
            room_metric.queued_count += 1
            room_metric.save()
        except Exception as e:
            logger.warning(
                f"[BULK_TAKE] metrics update failed for room {room.uuid}: {e}"
            )

        try:
            room.update_ticket_async()
        except Exception as e:
            logger.warning(
                f"[BULK_TAKE] update_ticket_async failed for room {room.uuid}: {e}"
            )
