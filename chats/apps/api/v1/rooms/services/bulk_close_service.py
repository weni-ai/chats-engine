import logging
from collections import defaultdict
from typing import Dict, List, Optional

from celery import group
from django.conf import settings
from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from chats.apps.accounts.models import User
from chats.apps.rooms.models import Room, RoomPin

logger = logging.getLogger(__name__)


class BulkCloseResult:
    """Result object for bulk close operation"""
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
            "errors": self.errors[:10] if self.errors else [],  # Limit to first 10 errors
            "failed_rooms": self.failed_rooms[:10] if self.failed_rooms else [],  # Limit to first 10
            "has_more_errors": len(self.errors) > 10,
        }


class BulkCloseService:
    """
    Service for bulk closing rooms with optimized database operations.

    Maintains all the logic from room.close() but optimized for batch processing:
    - Bulk update for room fields
    - Batch M2M operations for tags
    - Bulk delete for pins
    - Optimized InService status updates
    - Batched Celery task scheduling
    """

    def close(
        self,
        rooms: QuerySet[Room],
        room_tags_map: Dict[str, List[str]] = None,
        end_by: str = "",
        closed_by: Optional[User] = None,
    ) -> BulkCloseResult:
        """
        Close rooms in bulk with optimized database operations.

        Args:
            rooms: QuerySet of Room objects to close (should be prefetched)
            room_tags_map: Dict mapping room UUID to list of tag UUIDs (e.g., {"room-uuid": ["tag1", "tag2"]})
            end_by: String indicating who/what closed the rooms
            closed_by: User who closed the rooms

        Returns:
            BulkCloseResult with success/failure counts and error details

        Raises:
            ValueError: If rooms queryset is empty or invalid
        """
        result = BulkCloseResult()

        if room_tags_map is None:
            room_tags_map = {}

        # Convert to list to track individual rooms
        rooms_list = list(
            rooms.select_related(
                "queue__sector__project",
                "user",
                "closed_by"
            ).prefetch_related("tags")
        )

        if not rooms_list:
            logger.warning("BulkCloseService: No rooms provided")
            return result

        logger.info(f"BulkCloseService: Starting bulk close of {len(rooms_list)} rooms")

        # Separate active and already closed rooms
        active_rooms = []
        for room in rooms_list:
            if not room.is_active:
                result.add_failure(
                    room.uuid,
                    f"Room {room.uuid} is already closed"
                )
            else:
                active_rooms.append(room)

        if not active_rooms:
            logger.warning("BulkCloseService: No active rooms to close")
            return result

        now = timezone.now()
        successfully_closed = []

        # Process each room individually to track errors and validate required tags
        for room in active_rooms:
            try:
                # Validate room can be closed
                self._validate_room_can_close(room)

                # Validate required tags
                room_tags = room_tags_map.get(str(room.uuid), [])
                self._validate_required_tags(room, room_tags)

                successfully_closed.append(room)
                result.add_success()
            except Exception as e:
                error_msg = f"Room {room.uuid}: {str(e)}"
                result.add_failure(room.uuid, error_msg)
                logger.warning(f"Failed to prepare room for closing: {error_msg}")

        if not successfully_closed:
            logger.warning("BulkCloseService: No rooms could be closed")
            return result

        # Now perform bulk operations on successfully validated rooms
        try:
            with transaction.atomic():
                self._bulk_update_rooms(successfully_closed, now, end_by, closed_by)

                # Handle tags per room
                self._batch_handle_tags_per_room(successfully_closed, room_tags_map)

                # Bulk delete pins
                self._bulk_clear_pins(successfully_closed)

            # Handle InService status updates (grouped by agent)
            self._batch_update_inservice_status(successfully_closed)

            # Notify rooms via websocket (queue and users)
            self._batch_notify_rooms(successfully_closed)

            # Start queue priority routing for affected queues
            self._batch_start_queue_priority_routing(successfully_closed)

            # Schedule CSAT flow tasks in batch
            self._batch_schedule_csat_tasks(successfully_closed)

            # Schedule metrics tasks in batch
            self._batch_schedule_metrics_tasks(successfully_closed)


            logger.info(
                f"BulkCloseService: Successfully closed {result.success_count} rooms, "
                f"{result.failed_count} failed"
            )

        except Exception as e:
            logger.error(f"BulkCloseService: Critical error during bulk operations: {str(e)}")
            # Mark all as failed if bulk operation fails
            for room in successfully_closed:
                if room.uuid not in result.failed_rooms:
                    result.add_failure(room.uuid, f"Bulk operation failed: {str(e)}")
                    result.success_count -= 1  # Adjust success count

        return result

    def _validate_room_can_close(self, room: Room):
        """
        Validate that a room can be closed.
        Raises exception if validation fails.
        """
        # Check if room is already closed (double-check after initial filter)
        if not room.is_active:
            raise ValueError("Room is already closed")

        # Add any other validations needed
        if not room.queue:
            raise ValueError("Room has no queue assigned")

        if not hasattr(room.queue, 'sector'):
            raise ValueError("Queue has no sector assigned")

    def _validate_required_tags(self, room: Room, tags: List[str]):
        """
        Validate that required tags are provided for rooms that require them.
        Raises exception if validation fails.
        """
        # Check if queue requires tags
        if room.queue.required_tags:
            # Check if room already has tags or if new tags are being provided
            has_existing_tags = room.tags.exists()
            has_new_tags = len(tags) > 0

            if not has_existing_tags and not has_new_tags:
                raise ValueError("Tags are required for this queue but none were provided")

    def _bulk_update_rooms(
        self,
        rooms_list: List[Room],
        ended_at: timezone.datetime,
        end_by: str,
        closed_by: Optional[User]
    ):
        """
        Update room fields using bulk_update for performance.
        Single UPDATE query instead of N queries.
        """
        for room in rooms_list:
            room.is_active = False
            room.ended_at = ended_at
            room.ended_by = end_by
            room.closed_by = closed_by

        Room.objects.bulk_update(
            rooms_list,
            ["is_active", "ended_at", "ended_by", "closed_by"],
            batch_size=500
        )

        logger.debug(f"Bulk updated {len(rooms_list)} rooms")

    def _batch_handle_tags_per_room(self, rooms_list: List[Room], room_tags_map: Dict[str, List[str]]):
        """
        Handle tags per room, applying specific tags to each room.
        Each room can have different tags or no tags at all.

        Args:
            rooms_list: List of Room objects to update
            room_tags_map: Dict mapping room UUID to list of tag UUIDs
        """
        from chats.apps.sectors.models import SectorTag

        if not room_tags_map:
            logger.debug("No tags to apply to any rooms")
            return

        # Collect all unique tag UUIDs to validate in a single query
        all_tag_uuids = set()
        for tags in room_tags_map.values():
            all_tag_uuids.update(tags)

        if all_tag_uuids:
            # Validate all tags exist in a single query
            existing_tags = set(
                str(tag_uuid) for tag_uuid in SectorTag.objects.filter(
                    uuid__in=all_tag_uuids
                ).values_list("uuid", flat=True)
            )

            if len(existing_tags) != len(all_tag_uuids):
                missing = all_tag_uuids - existing_tags
                logger.warning(f"Some tags not found: {missing}")

        # Process each room's tags individually
        rooms_with_tags = 0
        for room in rooms_list:
            room_uuid_str = str(room.uuid)
            new_tags = room_tags_map.get(room_uuid_str, [])

            if not new_tags:
                continue  # Skip rooms with no tags specified

            # Get current tags for this room
            current_tag_ids = set(
                str(tag_uuid) for tag_uuid in room.tags.values_list("uuid", flat=True)
            )

            # Convert new tags to set of strings
            new_tag_ids = set(str(tag) for tag in new_tags)

            # Determine which tags to add and which to remove
            tags_to_add = new_tag_ids - current_tag_ids
            tags_to_remove = current_tag_ids - new_tag_ids

            if tags_to_add:
                room.tags.add(*tags_to_add)
            if tags_to_remove:
                room.tags.remove(*tags_to_remove)

            rooms_with_tags += 1

        logger.debug(f"Applied tags to {rooms_with_tags} rooms out of {len(rooms_list)}")

    def _bulk_clear_pins(self, rooms_list: List[Room]):
        """
        Clear all pins for the rooms in a single DELETE query.
        """
        room_ids = [room.pk for room in rooms_list]
        deleted_count, _ = RoomPin.objects.filter(room_id__in=room_ids).delete()

        logger.debug(f"Bulk deleted {deleted_count} pins for {len(rooms_list)} rooms")

    def _batch_update_inservice_status(self, rooms_list: List[Room]):
        """
        Update InService status for agents in batch.
        Groups by (user, project) to minimize queries.
        """
        from chats.apps.projects.usecases.status_service import InServiceStatusService

        # Group rooms by (user, project) to optimize queries
        user_project_map = defaultdict(set)

        for room in rooms_list:
            if not room.user:
                continue

            project = None
            if room.queue and hasattr(room.queue, "sector"):
                sector = room.queue.sector
                if sector and hasattr(sector, "project"):
                    project = sector.project

            if project:
                user_project_map[(room.user, project)].add(room)

        # Call InServiceStatusService for each unique (user, project) pair
        for (user, project), room_set in user_project_map.items():
            try:
                InServiceStatusService.room_closed(user, project)
            except Exception as e:
                logger.error(
                    f"Error updating InService status for user {user.email}, "
                    f"project {project.uuid}: {str(e)}"
                )

        logger.debug(
            f"Updated InService status for {len(user_project_map)} unique user-project pairs"
        )

    def _batch_notify_rooms(self, rooms_list: List[Room]):
        """
        Send websocket notifications for closed rooms.
        Notifies both queue and user channels so agents can see rooms were closed.
        Similar to individual close: notify_queue("close") and notify_user("close")
        """
        notified_count = 0

        for room in rooms_list:
            try:
                # Notify queue channel (for agents monitoring the queue)
                room.notify_queue("close", callback=True)

                # Notify user channel (for the assigned agent if any)
                room.notify_user("close")

                notified_count += 1
            except Exception as e:
                logger.warning(
                    f"Failed to notify room {room.uuid}: {str(e)}"
                )

        logger.debug(f"Notified {notified_count} rooms via websocket")

    def _batch_start_queue_priority_routing(self, rooms_list: List[Room]):
        """
        Start queue priority routing for unique queues.
        Groups rooms by queue and calls start_queue_priority_routing once per queue.
        This optimizes routing by processing each queue only once instead of N times.
        """
        from chats.apps.queues.utils import start_queue_priority_routing

        # Get unique queues from closed rooms
        unique_queues = set()
        for room in rooms_list:
            if room.queue:
                unique_queues.add(room.queue)

        if not unique_queues:
            return

        # Start priority routing for each unique queue
        for queue in unique_queues:
            try:
                logger.info(
                    f"Calling start_queue_priority_routing for queue {queue.uuid} "
                    f"from bulk close"
                )
                start_queue_priority_routing(queue)
            except Exception as e:
                logger.error(
                    f"Failed to start priority routing for queue {queue.uuid}: {str(e)}"
                )

        logger.debug(
            f"Started priority routing for {len(unique_queues)} unique queues "
            f"(from {len(rooms_list)} closed rooms)"
        )


    def _batch_schedule_csat_tasks(self, rooms_list: List[Room]):
        """
        Schedule CSAT flow tasks in batches using Celery groups.
        Only for rooms with CSAT enabled and assigned users.
        """
        from chats.apps.csat.tasks import start_csat_flow

        # Filter rooms eligible for CSAT
        csat_room_uuids = []
        for room in rooms_list:
            if (
                room.queue
                and room.queue.sector.is_csat_enabled
                and room.user
            ):
                csat_room_uuids.append(str(room.uuid))

        if not csat_room_uuids:
            logger.debug("No rooms eligible for CSAT")
            return

        # Batch CSAT tasks in groups of 100 to avoid overwhelming Celery
        batch_size = 100
        total_batches = (len(csat_room_uuids) + batch_size - 1) // batch_size

        def schedule_csat_batch():
            for i in range(0, len(csat_room_uuids), batch_size):
                batch = csat_room_uuids[i:i + batch_size]
                task_group = group(
                    start_csat_flow.s(room_uuid) for room_uuid in batch
                )
                task_group.apply_async()

        # Schedule after transaction commits
        transaction.on_commit(schedule_csat_batch)

        logger.debug(
            f"Scheduled {len(csat_room_uuids)} CSAT tasks in {total_batches} batches"
        )

    def _batch_schedule_metrics_tasks(self, rooms_list: List[Room]):
        """
        Schedule metrics generation tasks in batches.
        Uses Celery for async processing with batching.
        """
        from chats.apps.dashboard.tasks import close_metrics, generate_metrics

        room_uuids = [str(room.uuid) for room in rooms_list]

        if not room_uuids:
            return

        # Batch metrics tasks in groups of 100
        batch_size = 100
        total_batches = (len(room_uuids) + batch_size - 1) // batch_size

        def schedule_metrics_batch():
            if settings.USE_CELERY:
                # Schedule close_metrics tasks in batches
                for i in range(0, len(room_uuids), batch_size):
                    batch = room_uuids[i:i + batch_size]
                    task_group = group(
                        close_metrics.s(room_uuid)
                        for room_uuid in batch
                    )
                    task_group.apply_async(queue=settings.METRICS_CUSTOM_QUEUE)
            else:
                # Fallback: generate metrics synchronously (for testing)
                for room_uuid in room_uuids:
                    try:
                        generate_metrics(room_uuid)
                    except Exception as e:
                        logger.error(
                            f"Error generating metrics for room {room_uuid}: {str(e)}"
                        )

        # Schedule after transaction commits
        transaction.on_commit(schedule_metrics_batch)

        logger.debug(
            f"Scheduled {len(room_uuids)} metrics tasks in {total_batches} batches"
        )
