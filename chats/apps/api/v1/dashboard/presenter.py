import json

import pendulum
from django.db.models import Avg, Count, F, Q, Sum
from django.utils import timezone

from chats.apps.projects.models import ProjectPermission
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector


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
            rooms_filter["tags__uuid"] = filter.get("tag")
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
    tz = project.timezone
    initial_datetime = (
        timezone.now().astimezone(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    )
    rooms_filter = {}

    rooms_filter_in_progress_chats = {}
    rooms_filter_in_progress_chats["user__isnull"] = False

    rooms_filter_waiting_service = {}
    rooms_filter_waiting_service["user__isnull"] = True
    rooms_filter_waiting_service["is_active"] = True

    rooms_filter_closed = {}
    rooms_filter_closed["is_active"] = False

    if filter.get("start_date") and filter.get("end_date"):
        start_time = pendulum.parse(filter.get("start_date")).replace(tzinfo=tz)
        end_time = pendulum.parse(filter.get("end_date") + " 23:59:59").replace(
            tzinfo=tz
        )
        rooms_filter["created_on__range"] = [
            start_time,
            end_time,  # TODO: USE DATETIME IN END DATE
        ]
        rooms_filter_in_progress_chats["created_on__range"] = [
            start_time,
            end_time,  # TODO: USE DATETIME IN END DATE
        ]
        rooms_filter_waiting_service["created_on__range"] = [
            start_time,
            end_time,  # TODO: USE DATETIME IN END DATE
        ]
        rooms_filter_closed["ended_at__range"] = [
            start_time,
            end_time,  # TODO: USE DATETIME IN END DATE
        ]
        rooms_filter_in_progress_chats["is_active"] = False
    else:
        rooms_filter["created_on__gte"] = initial_datetime
        rooms_filter_in_progress_chats["is_active"] = True
        rooms_filter_closed["ended_at__gte"] = initial_datetime

    if filter.get("agent"):
        rooms_filter["user"] = filter.get("agent")
        rooms_filter_in_progress_chats["user"] = filter.get("agent")
        rooms_filter_closed["user"] = filter.get("agent")

    if filter.get("sector"):
        rooms_filter["queue__sector"] = filter.get("sector")
        rooms_filter_in_progress_chats["queue__sector"] = filter.get("sector")
        rooms_filter_waiting_service["queue__sector"] = filter.get("sector")
        rooms_filter_closed["queue__sector"] = filter.get("sector")
        if filter.get("tag"):
            rooms_filter["tags__uuid"] = filter.get("tag")
            rooms_filter_in_progress_chats["tags__uuid"] = filter.get("tag")
            rooms_filter_closed["tags__uuid"] = filter.get("tag")
    else:
        rooms_filter["queue__sector__project"] = project
        rooms_filter_in_progress_chats["queue__sector__project"] = project
        rooms_filter_waiting_service["queue__sector__project"] = project
        rooms_filter_closed["queue__sector__project"] = project

    data = {}
    metrics_rooms_count = Room.objects.filter(**rooms_filter).count()

    # in_progress
    active_chats = Room.objects.filter(**rooms_filter_in_progress_chats).count()

    # waiting_service
    queue_rooms = Room.objects.filter(**rooms_filter_waiting_service).count()

    # closed_rooms
    closed_rooms = Room.objects.filter(**rooms_filter_closed).count()

    # interaction_time
    interaction_value = Room.objects.filter(**rooms_filter).aggregate(
        interaction_time=Sum("metric__interaction_time")
    )
    if interaction_value and metrics_rooms_count > 0:
        interaction_time = interaction_value["interaction_time"] / metrics_rooms_count
    else:
        interaction_time = 0

    # response_time
    response_time_value = Room.objects.filter(**rooms_filter).aggregate(
        message_response_time=Sum("metric__message_response_time")
    )
    if response_time_value and metrics_rooms_count > 0:
        response_time = (
            response_time_value["message_response_time"] / metrics_rooms_count
        )
    else:
        response_time = 0

    # waiting_time
    waiting_time_value = Room.objects.filter(**rooms_filter).aggregate(
        waiting_time=Sum("metric__waiting_time")
    )
    if waiting_time_value and metrics_rooms_count > 0:
        waiting_time = waiting_time_value["waiting_time"] / metrics_rooms_count
    else:
        waiting_time = 0

    data = {
        "active_chats": active_chats,
        "queue_rooms": queue_rooms,
        "closed_rooms": closed_rooms,
        "interaction_time": interaction_time,
        "response_time": response_time,
        "waiting_time": waiting_time,
    }

    return data


def get_agents_data(project, filter):
    tz = project.timezone
    initial_datetime = (
        timezone.now().astimezone(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    )
    rooms_filter = {}
    closed_rooms = {}
    permission_filter = {"project": project}

    rooms_filter["user__rooms__is_active"] = True
    closed_rooms["user__rooms__is_active"] = False

    if filter.get("start_date") and filter.get("end_date"):
        start_time = pendulum.parse(filter.get("start_date")).replace(tzinfo=tz)
        end_time = pendulum.parse(filter.get("end_date") + " 23:59:59").replace(
            tzinfo=tz
        )
        rooms_filter["user__rooms__created_on__range"] = [
            start_time,
            end_time,  # TODO: USE DATETIME IN END DATE
        ]
        closed_rooms["user__rooms__ended_at__range"] = [
            start_time,
            end_time,  # TODO: USE DATETIME IN END DATE
        ]
    else:
        closed_rooms["user__rooms__ended_at__gte"] = initial_datetime

    if filter.get("agent"):
        rooms_filter["user"] = filter.get("agent")
        closed_rooms["user"] = filter.get("agent")

    if filter.get("sector"):
        rooms_filter["user__rooms__queue__sector"] = filter.get("sector")
        closed_rooms["user__rooms__queue__sector"] = filter.get("sector")
        if filter.get("tag"):
            rooms_filter["user__rooms__tags__uuid"] = filter.get("tag")
            closed_rooms["user__rooms__tags__uuid"] = filter.get("tag")
    else:
        rooms_filter["user__rooms__queue__sector__project"] = project
        closed_rooms["user__rooms__queue__sector__project"] = project
    queue_auth = (
        ProjectPermission.objects.filter(**permission_filter)
        .exclude(user__email__icontains="weni")
        .values(Name=F("user__first_name"))
        .annotate(
            opened_rooms=Count(
                "user__rooms",
                filter=Q(**rooms_filter),
                distinct=True,
            ),
            closed_rooms=Count(
                "user__rooms",
                filter=Q(**closed_rooms),
                distinct=True,
            ),
        )
    )

    data = json.dumps(list(queue_auth))
    return data


def get_sector_data(project, filter):
    tz = project.timezone
    initial_datetime = (
        timezone.now().astimezone(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    )

    model = Sector
    rooms_filter = {}
    model_filter = {"project": project}
    rooms_filter_prefix = "queues__"

    if filter.get("sector"):
        model = Queue
        rooms_filter_prefix = ""
        model_filter = {"sector": filter.get("sector")}
        rooms_filter["rooms__queue__sector"] = filter.get("sector")
        if filter.get("tag"):
            rooms_filter["rooms__tags__uuid"] = filter.get("tag")
        if filter.get("agent"):
            rooms_filter["rooms__user"] = filter.get("agent")
    else:
        rooms_filter[f"{rooms_filter_prefix}rooms__queue__sector__project"] = project
        if filter.get("agent"):
            rooms_filter[f"{rooms_filter_prefix}rooms__user"] = filter.get("agent")

    if filter.get("start_date") and filter.get("end_date"):
        start_time = pendulum.parse(filter.get("start_date")).replace(tzinfo=tz)
        end_time = pendulum.parse(filter.get("end_date") + " 23:59:59").replace(
            tzinfo=tz
        )
        rooms_filter[f"{rooms_filter_prefix}rooms__created_on__range"] = [
            start_time,
            end_time,  # TODO: USE DATETIME IN END DATE
        ]
    else:
        rooms_filter[f"{rooms_filter_prefix}rooms__created_on__gte"] = initial_datetime
    results = (
        model.objects.filter(**model_filter)
        .values(sector_name=F("name"))
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
        )
    ).values("name", "waiting_time", "response_time", "interact_time")

    data = json.dumps(list(results))
    return data
