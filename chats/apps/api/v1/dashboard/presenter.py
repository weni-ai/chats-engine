from django.utils import timezone
from chats.apps.projects.models import ProjectPermission
from chats.apps.queues.models import Queue

from chats.apps.rooms.models import Room

from django.db.models import Sum, Count, Q, Avg, F

from chats.apps.sectors.models import Sector
import json


def get_export_data(project, filter):
    initial_datetime = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    rooms_filter = {}

    if filter.get("start_date") and filter.get("end_date"):
        rooms_filter["created_on__range"] = [
            filter.get("start_date"),
            filter.get("end_date") + " 23:59:59",  # TODO: USE DATETIME IN END DATE
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


def get_general_data(project, filter):
    initial_datetime = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    rooms_filter = {}

    initial_datetime = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    rooms_filter = {}
    rooms_filter_active_chats = {}

    if filter.get("start_date") and filter.get("end_date"):
        rooms_filter["created_on__range"] = [
            filter.get("start_date"),
            filter.get("end_date") + " 23:59:59",  # TODO: USE DATETIME IN END DATE
        ]
        rooms_filter_active_chats["is_active"] = False
    else:
        rooms_filter["created_on__gte"] = initial_datetime
        rooms_filter_active_chats["is_active"] = True

    if filter.get("agent"):
        rooms_filter["user"] = filter.get("agent")

    if filter.get("sector"):
        rooms_filter["queue__sector"] = filter.get("sector")
        if filter.get("tag"):
            rooms_filter["tags__name"] = filter.get("tag")
    else:
        rooms_filter["queue__sector__project"] = project

    rooms_filter_active_chats.update(rooms_filter)
    rooms_filter_active_chats.pop("created_on__gte")

    data = {}

    metrics_rooms_count = Room.objects.filter(**rooms_filter).count()

    active_chats = Room.objects.filter(**rooms_filter_active_chats).count()

    interaction_value = Room.objects.filter(**rooms_filter).aggregate(
        interaction_time=Sum("metric__interaction_time")
    )
    if interaction_value and metrics_rooms_count > 0:
        interaction_time = interaction_value["interaction_time"] / metrics_rooms_count
    else:
        interaction_time = 0

    response_time_value = Room.objects.filter(**rooms_filter).aggregate(
        message_response_time=Sum("metric__message_response_time")
    )
    if response_time_value and metrics_rooms_count > 0:
        response_time = (
            response_time_value["message_response_time"] / metrics_rooms_count
        )
    else:
        response_time = 0

    waiting_time_value = Room.objects.filter(**rooms_filter).aggregate(
        waiting_time=Sum("metric__waiting_time")
    )
    if waiting_time_value and metrics_rooms_count > 0:
        waiting_time = waiting_time_value["waiting_time"] / metrics_rooms_count
    else:
        waiting_time = 0

    data = {
        "active_chats": active_chats,
        "interaction_time": interaction_time,
        "response_time": response_time,
        "waiting_time": waiting_time,
    }

    return data


def get_agents_data(project, filter):
    rooms_filter = {}
    permission_filter = {"project": project}

    if filter.get("start_date") and filter.get("end_date"):
        rooms_filter["user__rooms__created_on__range"] = [
            filter.get("start_date"),
            filter.get("end_date") + " 23:59:59",  # TODO: USE DATETIME IN END DATE
        ]
        rooms_filter["user__rooms__is_active"] = False
    else:
        rooms_filter["user__rooms__is_active"] = True
        permission_filter["status"] = "ONLINE"

    if filter.get("agent"):
        rooms_filter["user"] = filter.get("agent")

    if filter.get("sector"):
        rooms_filter["user__rooms__queue__sector"] = filter.get("sector")
        if filter.get("tag"):
            rooms_filter["user__rooms__tags__name"] = filter.get("tag")
    else:
        rooms_filter["user__rooms__queue__sector__project"] = project

    queue_auth = (
        ProjectPermission.objects.filter(**permission_filter)
        .values(Agent_Name=F("user__first_name"))
        .annotate(
            count=Count(
                "user__rooms",
                filter=Q(**rooms_filter),
                distinct=True,
            )
        )
    ).values("Agent_Name", "count")

    data = json.dumps(list(queue_auth))
    return data


def get_sector_data(project, filter):
    initial_datetime = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

    model = Sector
    rooms_filter = {}
    model_filter = {"project": project}
    rooms_filter_prefix = "queues__"
    online_agents = Count(f"{rooms_filter_prefix}rooms")

    if filter.get("sector"):
        model = Queue
        rooms_filter_prefix = ""
        model_filter = {"sector": filter.get("sector")}
        rooms_filter["rooms__queue__sector"] = filter.get("sector")
        if filter.get("tag"):
            rooms_filter["rooms__tags__name"] = filter.get("tag")
        if filter.get("agent"):
            rooms_filter["rooms__user"] = filter.get("agent")
    else:
        rooms_filter[f"{rooms_filter_prefix}rooms__queue__sector__project"] = project
        if filter.get("agent"):
            rooms_filter[f"{rooms_filter_prefix}rooms__user"] = filter.get("agent")

    if filter.get("start_date") and filter.get("end_date"):
        rooms_filter[f"{rooms_filter_prefix}rooms__created_on__range"] = [
            filter.get("start_date"),
            filter.get("end_date") + " 23:59:59",  # TODO: USE DATETIME IN END DATE
        ]

        online_agents_filter = {}
        online_agents_filter[f"{rooms_filter_prefix}rooms__created_on__range"] = [
            filter.get("start_date"),
            filter.get("end_date") + " 23:59:59",  # TODO: USE DATETIME IN END DATE
        ]
        online_agents = Count(
            f"{rooms_filter_prefix}rooms",
            filter=Q(**online_agents_filter),
        )

    else:
        rooms_filter[f"{rooms_filter_prefix}rooms__created_on__gte"] = initial_datetime
        online_agents_filter = {
            f"{rooms_filter_prefix}authorizations__permission__status": "ONLINE"
        }
        online_agents = Count(
            f"{rooms_filter_prefix}authorizations__permission",
            filter=Q(**online_agents_filter),
            distinct=True,
        )
    results = (
        model.objects.filter(**model_filter)
        .values("name")
        .annotate(
            waiting_time=Avg(
                f"{rooms_filter_prefix}rooms__metric__waiting_time",
                filter=Q(**rooms_filter),
            ),
            response_time=Avg(
                f"{rooms_filter_prefix}rooms__metric__message_response_time",
                filter=Q(**rooms_filter),
            ),
            interact_time=Avg(
                f"{rooms_filter_prefix}rooms__metric__interaction_time",
                filter=Q(**rooms_filter),
            ),
            online_agents=online_agents,
        )
    ).values("name", "waiting_time", "response_time", "interact_time", "online_agents")

    data = json.dumps(list(results))
    return data
