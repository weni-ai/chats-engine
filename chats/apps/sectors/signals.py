from django.db.models.signals import pre_delete
from django.dispatch import receiver

from chats.apps.sectors.models import SectorAuthorization


@receiver(pre_delete, sender=SectorAuthorization)
def requeue_rooms_on_sector_auth_delete(sender, instance, **kwargs):
    """
    When an agent is removed from a sector, return their active rooms
    in that sector's queues back to the queue so they can be reassigned.
    """
    from chats.apps.rooms.models import Room
    from chats.apps.rooms.services import requeue_agent_rooms

    rooms = Room.objects.filter(
        user=instance.permission.user,
        queue__sector=instance.sector,
        is_active=True,
    )
    requeue_agent_rooms(rooms)
