from queue import Queue

from chats.apps.rooms.models import Room


class QueueRouterService:
    def __init__(self, queue: Queue):
        self.queue = queue

    def route_rooms(self):
        rooms = Room.objects.filter(queue=self.queue)

        if not rooms.exists():
            return

        sector = self.queue.sector
