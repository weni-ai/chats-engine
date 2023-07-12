from chats.apps.dashboard.models import RoomMetrics
from chats.apps.rooms.models import Room
from chats.celery import app


@app.task(name="close_metrics")
def close_metrics(room: str):
    room = Room.objects.get(pk=room)
    messages_contact = (
        room.messages.filter(contact__isnull=False).order_by("created_on").first()
    )
    messages_agent = (
        room.messages.filter(user__isnull=False).order_by("created_on").first()
    )

    time_message_contact = 0
    time_message_agent = 0

    if messages_agent and messages_contact:
        time_message_agent = messages_agent.created_on.timestamp()
        time_message_contact = messages_contact.created_on.timestamp()
    else:
        time_message_agent = 0
        time_message_contact = 0

    difference_time = time_message_agent - time_message_contact
    interaction_time = room.ended_at - room.created_on

    metric_room = RoomMetrics.objects.get_or_create(room=room)[0]
    metric_room.message_response_time = difference_time
    metric_room.interaction_time = interaction_time.total_seconds()
    metric_room.save()
