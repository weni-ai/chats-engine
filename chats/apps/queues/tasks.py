from uuid import UUID
from chats.apps.queues.models import Queue
from chats.apps.queues.services import QueueRouterService
from chats.celery import app


@app.task
def start_queue_priority_routing(queue_id: UUID):
    """
    Route rooms to available agents.
    """
    queue = Queue.objects.get(id=queue_id)

    QueueRouterService(queue).route_rooms()
