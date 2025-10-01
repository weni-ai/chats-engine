from chats.celery import app
from chats.apps.rooms.models import Room
from chats.apps.csat.services import CSATFlowService


@app.task
def start_csat_flow(room_uuid: str):
    room = Room.objects.get(uuid=room_uuid)

    CSATFlowService().start_csat_flow(room)
