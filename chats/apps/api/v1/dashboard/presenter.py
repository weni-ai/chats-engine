import pendulum
from django.utils import timezone

from chats.apps.rooms.models import Room


def get_export_data(project, filter):
    tz = project.timezone
    initial_datetime = (
        timezone.now().astimezone(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    )
    rooms_filter = {}

    if filter.get("start_date") and filter.get("end_date"):
        start_time = pendulum.parse(filter.get("start_date")).replace(tzinfo=tz)
        end_time = pendulum.parse(filter.get("end_date") + " 23:59:59").replace(
            tzinfo=tz
        )
        rooms_filter["created_on__range"] = [
            start_time,
            end_time,  # TODO: USE DATETIME IN END DATE
        ]
    else:
        rooms_filter["created_on__gte"] = initial_datetime

    if filter.get("agent"):
        rooms_filter["user"] = filter.get("agent")

    if filter.get("sector"):
        rooms_filter["queue__sector"] = filter.get("sector")
        if filter.get("tag"):
            rooms_filter["tags__name"] = filter.get("tag")
    else:
        rooms_filter["queue__sector__project"] = project

    export_data = Room.objects.filter(**rooms_filter).values_list(
        "metric__room__queue__name",
        "metric__waiting_time",
        "metric__message_response_time",
        "metric__interaction_time",
        "is_active",
    )

    return export_data
