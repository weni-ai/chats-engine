from django.db.models.signals import pre_delete
from django.dispatch import receiver

from chats.apps.queues.models import QueueAuthorization
from chats.apps.rooms.models import Room
from chats.apps.rooms.tasks import requeue_agent_rooms_task


@receiver(pre_delete, sender=QueueAuthorization)
def requeue_rooms_on_queue_auth_delete(sender, instance, **kwargs):
    """
    When an agent is removed from a queue, return their active rooms
    in that queue back to the queue so they can be reassigned.
    """
    room_uuids = list(
        Room.objects.filter(
            user=instance.permission.user,
            queue=instance.queue,
            is_active=True,
        ).values_list("uuid", flat=True)
    )
    if room_uuids:
        requeue_agent_rooms_task.delay([str(u) for u in room_uuids])
