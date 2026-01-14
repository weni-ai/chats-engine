import logging
from django.db.models.signals import pre_delete
from django.dispatch import receiver

from chats.apps.projects.models import ProjectPermission
from chats.apps.queues.models import QueueAuthorization
from chats.apps.sectors.models import SectorAuthorization
from chats.apps.rooms.models import Room
from chats.apps.rooms.utils import create_transfer_json
from chats.apps.rooms.choices import RoomFeedbackMethods
from chats.apps.rooms.views import create_room_feedback_message

logger = logging.getLogger(__name__)


def transfer_user_rooms_to_queue(user, project):
    """
    Transfer all active rooms from a user back to their respective queues
    when the user is removed from a project.
    """
    # Get all active rooms assigned to this user in this project
    active_rooms = Room.objects.filter(
        user=user,
        is_active=True,
        queue__sector__project=project,
        queue__isnull=False
    ).select_related('queue', 'contact')

    rooms_count = active_rooms.count()

    if rooms_count == 0:
        logger.info(
            f"No active rooms to transfer for user {user.email} in project {project.uuid}"
        )
        return

    logger.info(
        f"Transferring {rooms_count} active room(s) from user {user.email} "
        f"back to queue before removing from project {project.uuid}"
    )

    for room in active_rooms:
        # Store the original queue and user
        original_queue = room.queue
        original_user = room.user

        # Create transfer feedback
        feedback = create_transfer_json(
            action="transfer",
            from_=original_user,
            to=original_queue,
        )

        # Transfer room back to queue
        room.user = None
        room.save()

        # Add transfer to history
        room.add_transfer_to_history(feedback)

        # Create feedback message
        create_room_feedback_message(
            room, feedback, method=RoomFeedbackMethods.ROOM_TRANSFER
        )

        # Notify relevant parties
        room.notify_user("update", user=original_user)
        room.notify_queue("update")

        logger.info(
            f"Room {room.uuid} transferred from user {user.email} "
            f"to queue {original_queue.uuid}"
        )


@receiver(pre_delete, sender=ProjectPermission)
def handle_project_permission_deletion(sender, instance, **kwargs):
    """
    Handle the deletion of a ProjectPermission.
    Transfer all active rooms back to their queues before removing the user.
    """
    user = instance.user
    project = instance.project

    logger.info(
        f"ProjectPermission being deleted for user {user.email} "
        f"in project {project.uuid}"
    )

    transfer_user_rooms_to_queue(user, project)


@receiver(pre_delete, sender=QueueAuthorization)
def handle_queue_authorization_deletion(sender, instance, **kwargs):
    """
    Handle the deletion of a QueueAuthorization.
    Transfer rooms from this specific queue back to the queue.
    """
    user = instance.user
    queue = instance.queue
    project = queue.project

    logger.info(
        f"QueueAuthorization being deleted for user {user.email} "
        f"in queue {queue.uuid}"
    )

    # Check if user still has other authorizations in this project
    # If they have ProjectPermission as admin or other queue/sector auths, 
    # we only remove rooms from this specific queue
    has_other_auths = (
        ProjectPermission.objects.filter(
            user=user, 
            project=project
        ).exclude(
            uuid=getattr(instance.permission, 'uuid', None)
        ).exists()
    )

    if has_other_auths:
        # Only transfer rooms from this specific queue
        active_rooms = Room.objects.filter(
            user=user,
            is_active=True,
            queue=queue
        ).select_related('queue', 'contact')

        rooms_count = active_rooms.count()

        if rooms_count == 0:
            logger.info(
                f"No active rooms in queue {queue.uuid} for user {user.email}"
            )
            return

        logger.info(
            f"Transferring {rooms_count} room(s) from queue {queue.uuid} "
            f"back to queue for user {user.email}"
        )

        for room in active_rooms:
            original_user = room.user

            feedback = create_transfer_json(
                action="transfer",
                from_=original_user,
                to=queue,
            )

            room.user = None
            room.save()

            room.add_transfer_to_history(feedback)
            create_room_feedback_message(
                room, feedback, method=RoomFeedbackMethods.ROOM_TRANSFER
            )

            room.notify_user("update", user=original_user)
            room.notify_queue("update")

            logger.info(f"Room {room.uuid} transferred back to queue {queue.uuid}")


@receiver(pre_delete, sender=SectorAuthorization)
def handle_sector_authorization_deletion(sender, instance, **kwargs):
    """
    Handle the deletion of a SectorAuthorization.
    Transfer rooms from queues in this sector back to their queues.
    """
    user = instance.user
    sector = instance.sector
    project = sector.project

    logger.info(
        f"SectorAuthorization being deleted for user {user.email} "
        f"in sector {sector.uuid}"
    )

    # Check if user still has other authorizations in this project
    has_other_auths = (
        ProjectPermission.objects.filter(
            user=user,
            project=project
        ).exclude(
            uuid=getattr(instance.permission, 'uuid', None)
        ).exists()
    )

    if has_other_auths:
        # Only transfer rooms from queues in this sector
        active_rooms = Room.objects.filter(
            user=user,
            is_active=True,
            queue__sector=sector
        ).select_related('queue', 'contact')

        rooms_count = active_rooms.count()

        if rooms_count == 0:
            logger.info(
                f"No active rooms in sector {sector.uuid} for user {user.email}"
            )
            return

        logger.info(
            f"Transferring {rooms_count} room(s) from sector {sector.uuid} "
            f"back to their queues for user {user.email}"
        )

        for room in active_rooms:
            original_queue = room.queue
            original_user = room.user

            feedback = create_transfer_json(
                action="transfer",
                from_=original_user,
                to=original_queue,
            )

            room.user = None
            room.save()

            room.add_transfer_to_history(feedback)
            create_room_feedback_message(
                room, feedback, method=RoomFeedbackMethods.ROOM_TRANSFER
            )

            room.notify_user("update", user=original_user)
            room.notify_queue("update")

            logger.info(
                f"Room {room.uuid} transferred back to queue {original_queue.uuid}"
            )