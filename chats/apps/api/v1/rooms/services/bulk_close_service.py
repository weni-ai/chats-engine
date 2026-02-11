import logging
import time
from typing import Dict, List, Optional

from django.conf import settings
from django.db.models import QuerySet

from chats.apps.accounts.models import User
from chats.apps.rooms.models import Room
from chats.apps.rooms.views import close_room

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
            "errors": self.errors[:10] if self.errors else [],
            "failed_rooms": self.failed_rooms[:10] if self.failed_rooms else [],
            "has_more_errors": len(self.errors) > 10,
        }


class BulkCloseService:
    """
    Service for closing multiple rooms using the existing room.close() method.

    Processes rooms in configurable batches (settings.BULK_CLOSE_BATCH_SIZE)
    to avoid overwhelming the database and external dependencies.
    Each room is closed individually via room.close(), preserving all
    existing business logic (tags, pins, InService status, CSAT, etc.).
    """

    def close(
        self,
        rooms: QuerySet[Room],
        room_tags_map: Dict[str, List[str]] = None,
        end_by: str = "",
        closed_by: Optional[User] = None,
    ) -> BulkCloseResult:
        """
        Close rooms using room.close() in batches.

        Args:
            rooms: QuerySet of Room objects to close.
            room_tags_map: Dict mapping room UUID to list of tag UUIDs.
            end_by: String indicating who/what closed the rooms.
            closed_by: User who closed the rooms.

        Returns:
            BulkCloseResult with success/failure counts and error details.
        """
        result = BulkCloseResult()

        if room_tags_map is None:
            room_tags_map = {}

        batch_size = getattr(settings, "BULK_CLOSE_BATCH_SIZE", 200)

        rooms_list = list(
            rooms.select_related(
                "queue__sector__project",
                "user",
            ).prefetch_related("tags")
        )

        if not rooms_list:
            logger.warning("[BULK_CLOSE] No rooms provided")
            return result

        total = len(rooms_list)
        total_batches = (total + batch_size - 1) // batch_size

        logger.info(
            f"[BULK_CLOSE] Starting: {total} rooms in {total_batches} "
            f"batch(es) of {batch_size}"
        )

        start_time = time.perf_counter()

        for batch_index in range(0, total, batch_size):
            batch = rooms_list[batch_index : batch_index + batch_size]
            batch_number = batch_index // batch_size + 1

            logger.info(
                f"[BULK_CLOSE] Processing batch {batch_number}/{total_batches} "
                f"({len(batch)} rooms)"
            )

            for room in batch:
                try:
                    tags = room_tags_map.get(str(room.uuid), [])
                    room.close(tags=tags, end_by=end_by, closed_by=closed_by)
                    close_room(str(room.uuid))
                    result.add_success()
                except Exception as e:
                    error_msg = f"Room {room.uuid}: {str(e)}"
                    result.add_failure(room.uuid, error_msg)
                    logger.warning(f"[BULK_CLOSE] Failed to close room: {error_msg}")

            # Small pause between batches to relieve DB pressure
            has_more_batches = batch_index + batch_size < total
            if has_more_batches:
                time.sleep(0.1)

        elapsed = time.perf_counter() - start_time

        logger.info(
            f"[BULK_CLOSE] Completed: {result.success_count} succeeded, "
            f"{result.failed_count} failed - {elapsed:.2f}s"
        )

        return result
