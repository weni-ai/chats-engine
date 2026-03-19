from django.db.models.signals import pre_delete
from django.dispatch import receiver

from chats.apps.rooms.models import Room
from chats.apps.rooms.tasks import requeue_agent_rooms_task
from chats.apps.sectors.models import SectorAuthorization


@receiver(pre_delete, sender=SectorAuthorization)
def requeue_rooms_on_sector_auth_delete(sender, instance, **kwargs):
    """
    When an agent is removed from a sector, return their active rooms
    in that sector's queues back to the queue so they can be reassigned.
    """
    room_uuids = list(
        Room.objects.filter(
            user=instance.permission.user,
            queue__sector=instance.sector,
            is_active=True,
        ).values_list("uuid", flat=True)
    )
    if room_uuids:
        requeue_agent_rooms_task.delay([str(u) for u in room_uuids])
