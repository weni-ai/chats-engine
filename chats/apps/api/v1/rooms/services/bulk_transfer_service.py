import logging
import time
from typing import Dict, Optional

from django.conf import settings
from django.db.models import QuerySet

from chats.apps.accounts.models import User
from chats.apps.dashboard.models import RoomMetrics
from chats.apps.dashboard.utils import calculate_last_queue_waiting_time
from chats.apps.projects.models.models import ProjectPermission
from chats.apps.queues.models import Queue
from chats.apps.queues.utils import start_queue_priority_routing
from chats.apps.rooms.choices import RoomFeedbackMethods
from chats.apps.rooms.models import Room
from chats.apps.rooms.utils import create_transfer_json
from chats.apps.rooms.views import create_room_feedback_message


logger = logging.getLogger(__name__)


class BulkTransferResult:
    """Result object for bulk transfer operation"""

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


class BulkTransferService:
    """
    Service for bulk transferring rooms.

    Processes rooms in configurable batches (settings.BULK_TRANSFER_BATCH_SIZE)
    to avoid overwhelming the database and external dependencies.
    Each room is individually transferred, preserving all existing business
    logic (metrics, feedback messages, notifications, automatic messages,
    ticket updates, etc.).

    Queue priority routing is triggered once per unique queue at the end of
    each batch instead of per-room.
    """

    def _get_rooms_projects(self, rooms):
        return set(
            rooms.values_list("queue__sector__project__uuid", flat=True).distinct()
        )

    def _validate_queue(self, rooms, queue: Optional[Queue]):
        if not queue:
            return None

        projects = self._get_rooms_projects(rooms)
        queue_project = queue.sector.project.uuid
        for project in projects:
            if project != queue_project:
                return "Cannot transfer rooms from a project to another"
        return None

    def _validate_user(self, rooms, user: Optional[User]):
        if not user:
            return None

        projects = self._get_rooms_projects(rooms)
        user_projects = set(
            ProjectPermission.objects.filter(user=user).values_list(
                "project__uuid", flat=True
            )
        )
        for project in projects:
            if project not in user_projects:
                return f"User {user.email} has no permission on the project {project}"
        return None

    def _transfer_user_and_queue(
        self, room: Room, user: User, queue: Queue, user_request: User
    ):
        old_user = room.user
        old_queue = room.queue

        room.user = user
        room.queue = queue
        room.save()

        if not old_user:
            metrics = RoomMetrics.objects.get_or_create(room=room)[0]
            metrics.waiting_time += calculate_last_queue_waiting_time(room)
            metrics.queued_count += 1
            metrics.save()

        feedback_queue = create_transfer_json(
            action="transfer",
            from_=old_queue,
            to=queue,
            requested_by=user_request,
        )
        feedback_user = create_transfer_json(
            action="transfer",
            from_=old_user,
            to=user,
            requested_by=user_request,
        )

        create_room_feedback_message(
            room,
            feedback_queue,
            method=RoomFeedbackMethods.ROOM_TRANSFER,
            requested_by=user_request,
        )
        create_room_feedback_message(
            room,
            feedback_user,
            method=RoomFeedbackMethods.ROOM_TRANSFER,
            requested_by=user_request,
        )

        room.notify_queue("update")
        room.notify_user("update", user=old_user)
        room.notify_user("update")

        room.mark_notes_as_non_deletable()
        room.update_ticket_async()

    def _transfer_user(self, room: Room, user: User, user_request: User):
        old_user = room.user
        transfer_user = room.user if room.user else user_request

        feedback_user = create_transfer_json(
            action="transfer",
            from_=old_user,
            to=transfer_user,
            requested_by=user_request,
        )

        old_user_assigned_at = room.user_assigned_at

        room.user = user
        room.save()

        if not old_user:
            metrics = RoomMetrics.objects.get_or_create(room=room)[0]
            metrics.waiting_time += calculate_last_queue_waiting_time(room)
            metrics.queued_count += 1
            metrics.save()

        create_room_feedback_message(
            room,
            feedback_user,
            method=RoomFeedbackMethods.ROOM_TRANSFER,
            requested_by=user_request,
        )

        if old_user:
            room.notify_user("update", user=old_user)
        else:
            room.notify_user("update", user=transfer_user)
        room.notify_user("update")
        room.notify_queue("update")

        room.update_ticket()
        room.mark_notes_as_non_deletable()

        if (
            not old_user_assigned_at
            and room.queue.sector.is_automatic_message_active
            and room.queue.sector.automatic_message_text
        ):
            room.send_automatic_message()

    def _transfer_queue(self, room: Room, queue: Queue, user_request: User):
        transfer_user = room.user if room.user else user_request

        feedback = create_transfer_json(
            action="transfer",
            from_=transfer_user,
            to=queue,
            requested_by=user_request,
        )
        room.user = None
        room.queue = queue
        room.save()

        create_room_feedback_message(
            room,
            feedback,
            method=RoomFeedbackMethods.ROOM_TRANSFER,
            requested_by=user_request,
        )

        room.notify_user("update", user=transfer_user)
        room.notify_queue("update")

        room.mark_notes_as_non_deletable()

    def transfer(
        self,
        rooms: QuerySet[Room],
        user_request: User,
        user: Optional[User] = None,
        queue: Optional[Queue] = None,
    ) -> BulkTransferResult:
        result = BulkTransferResult()

        validation_error = self._validate_queue(rooms, queue)
        if validation_error:
            for room in rooms:
                result.add_failure(room.uuid, validation_error)
            return result

        validation_error = self._validate_user(rooms, user)
        if validation_error:
            for room in rooms:
                result.add_failure(room.uuid, validation_error)
            return result

        batch_size = getattr(settings, "BULK_TRANSFER_BATCH_SIZE", 50)

        room_pks = list(rooms.values_list("pk", flat=True))

        if not room_pks:
            logger.warning("[BULK_TRANSFER] No rooms provided")
            return result

        total = len(room_pks)
        total_batches = (total + batch_size - 1) // batch_size

        logger.info(
            f"[BULK_TRANSFER] Starting: {total} rooms in {total_batches} "
            f"batch(es) of {batch_size} for user {user_request.email}"
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
                f"[BULK_TRANSFER] Processing batch {batch_number}/{total_batches} "
                f"({len(batch)} rooms)"
            )

            affected_queue_ids = set()

            for room in batch:
                try:
                    if user and queue:
                        self._transfer_user_and_queue(room, user, queue, user_request)
                    elif user:
                        self._transfer_user(room, user, user_request)
                    elif queue:
                        self._transfer_queue(room, queue, user_request)

                    result.add_success()

                    if room.queue_id:
                        affected_queue_ids.add(room.queue_id)

                except Exception as e:
                    error_msg = f"Room {room.uuid}: {str(e)}"
                    result.add_failure(room.uuid, error_msg)
                    logger.warning(
                        f"[BULK_TRANSFER] Failed to transfer room: {error_msg}"
                    )

            for queue_id in affected_queue_ids:
                try:
                    q = Queue.objects.get(pk=queue_id)
                    start_queue_priority_routing(q)
                except Exception as e:
                    logger.warning(
                        f"[BULK_TRANSFER] Failed to start routing for queue "
                        f"{queue_id}: {str(e)}"
                    )

            has_more_batches = batch_index + batch_size < total
            if has_more_batches:
                time.sleep(0.1)

        elapsed = time.perf_counter() - start_time

        logger.info(
            f"[BULK_TRANSFER] Completed: {result.success_count} succeeded, "
            f"{result.failed_count} failed - {elapsed:.2f}s"
        )

        return result
