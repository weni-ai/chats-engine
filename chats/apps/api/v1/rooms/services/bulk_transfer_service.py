import logging
from typing import Optional

from chats.apps.accounts.models import User
from chats.apps.queues.utils import start_queue_priority_routing
from chats.apps.rooms.choices import RoomFeedbackMethods
from chats.apps.rooms.models import Room
from chats.apps.queues.models import Queue
from chats.apps.rooms.utils import create_transfer_json
from chats.apps.rooms.views import create_room_feedback_message


logger = logging.getLogger(__name__)


class BulkTransferService:
    """
    Service for bulk transferring rooms.
    """

    def transfer_user_and_queue(self, rooms: list[Room], user: User, queue: Queue):
        for room in rooms:
            old_user = room.user
            old_queue = room.queue

            room.user = user
            room.queue = queue

            room.save()

            feedback_queue = create_transfer_json(
                action="transfer",
                from_=old_queue,
                to=queue,
            )
            feedback_user = create_transfer_json(
                action="transfer",
                from_=old_user,
                to=user,
            )

        create_room_feedback_message(
            room, feedback_queue, method=RoomFeedbackMethods.ROOM_TRANSFER
        )
        create_room_feedback_message(
            room, feedback_user, method=RoomFeedbackMethods.ROOM_TRANSFER
        )
        room.notify_queue("update")
        room.notify_user("update", user=old_user)
        room.notify_user("update")

        logger.info(
            "Starting queue priority routing for queue %s from bulk transfer to user %s",
            queue.uuid,
            user.email,
        )
        start_queue_priority_routing(queue)

        room.mark_notes_as_non_deletable()
        room.update_ticket_async()

    def transfer_user(self, rooms: list[Room], user: User, user_request: User):
        for room in rooms:
            old_user = room.user

            transfer_user = room.user if room.user else user_request

            feedback_user = create_transfer_json(
                action="transfer",
                from_=old_user,
                to=transfer_user,
            )

            old_user_assigned_at = room.user_assigned_at

            room.user = user
            room.save()

            logger.info(
                "Starting queue priority routing for room %s from bulk transfer to user %s",
                room.uuid,
                user.email,
            )
            start_queue_priority_routing(room.queue)

            create_room_feedback_message(
                room, feedback_user, method=RoomFeedbackMethods.ROOM_TRANSFER
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

    def transfer_queue(self, rooms: list[Room], queue: Queue, user_request: User):
        for room in rooms:
            transfer_user = room.user if room.user else user_request

            feedback = create_transfer_json(
                action="transfer",
                from_=transfer_user,
                to=queue,
            )
            room.user = None
            room.queue = queue
            room.save()

            create_room_feedback_message(
                room, feedback, method=RoomFeedbackMethods.ROOM_TRANSFER
            )
            room.notify_user("update", user=transfer_user)
            room.notify_queue("update")

            logger.info(
                "Starting queue priority routing for room %s from bulk transfer to queue %s",
                room.uuid,
                queue.uuid,
            )
            start_queue_priority_routing(queue)

            # Mark all notes as non-deletable when room is transferred
            room.mark_notes_as_non_deletable()

    def transfer(
        self,
        rooms: list[Room],
        user_request: User,
        user: Optional[User] = None,
        queue: Optional[Queue] = None,
    ):
        """
        Transfer the rooms.
        """

        if user and queue:
            self.transfer_user_and_queue(rooms, user, queue)
        elif user:
            self.transfer_user(rooms, user, user_request)
        elif queue:
            self.transfer_queue(rooms, queue)
