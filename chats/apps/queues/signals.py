from django.db.models.signals import pre_delete
from django.dispatch import receiver

from chats.apps.queues.models import QueueAuthorization


@receiver(pre_delete, sender=QueueAuthorization)
def requeue_rooms_on_queue_auth_delete(sender, instance, **kwargs):
    """
    When an agent is removed from a queue, return their active rooms
    in that queue back to the queue so they can be reassigned.
    """
    from chats.apps.rooms.models import Room
    from chats.apps.rooms.services import requeue_agent_rooms

    rooms = Room.objects.filter(
        user=instance.permission.user,
        queue=instance.queue,
        is_active=True,
    )
    requeue_agent_rooms(rooms)
