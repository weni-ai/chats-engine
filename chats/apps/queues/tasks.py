from uuid import UUID
from chats.apps.queues.models import Queue
from chats.apps.queues.services import QueueRouterService
from chats.celery import app


@app.task
def route_queue_rooms(queue_id: UUID):
    """
    Route rooms to available agents for a queue in a project
    configured to use queue priority routing.
    """
    queue = Queue.objects.get(id=queue_id)

    QueueRouterService(queue).route_rooms()
