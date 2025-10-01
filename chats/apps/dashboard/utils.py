import logging
from datetime import timedelta
from typing import TYPE_CHECKING

from django.db.models import Q
from django.utils import timezone
from pendulum.parser import parse as pendulum_parse

logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from django.db.models import QuerySet

    from chats.apps.msgs.models import Message
    from chats.apps.rooms.models import Room


def calculate_response_time(room: "Room") -> int:
    """
    Calculate the average response time for a room.
    """
    room_creation_time = room.created_on

    messages: QuerySet["Message"] = room.messages.filter(
        (Q(user__isnull=False) | Q(contact__isnull=False))
        & Q(created_on__gte=room_creation_time)
    ).order_by("created_on")

    if not messages.exists():
        return 0

    total_response_time_sum = timedelta(0)
    agent_responses_count = 0

    last_time = room_creation_time
    last_message_was_from_agent = False

    for message in messages:
        if message.contact:
            last_time = message.created_on
            last_message_was_from_agent = False
            continue

        if message.user:
            if last_message_was_from_agent:
                continue

            last_message_was_from_agent = True

            response_duration = message.created_on - last_time
            total_response_time_sum += response_duration
            agent_responses_count += 1

    if agent_responses_count == 0:
        return 0

    average_response_seconds = (
        total_response_time_sum.total_seconds() / agent_responses_count
    )
    return int(average_response_seconds)


def calculate_last_queue_waiting_time(room: "Room"):
    """
    Calculate waiting time for a room.
    """

    if not room.added_to_queue_at:
        return (timezone.now() - room.created_on).total_seconds()

    return int((timezone.now() - room.added_to_queue_at).total_seconds())


<<<<<<< HEAD
def parse_date_filter(date_value, is_end_date=False, tz=None):
    """Convert string or datetime to datetime with timezone"""
    if isinstance(date_value, str):
        if 'T' in date_value or ':' in date_value:
            parsed_date = pendulum_parse(date_value)
        else:
            if is_end_date:
                parsed_date = pendulum_parse(date_value + " 23:59:59")
            else:
                parsed_date = pendulum_parse(date_value)
        
        return parsed_date.replace(tzinfo=tz)
    else:
        if is_end_date:
            return date_value.replace(
                hour=23, minute=59, second=59, microsecond=999999, tzinfo=tz
            )
        return date_value.replace(tzinfo=tz)
=======
def calculate_first_response_time(room: "Room") -> int:
    """
    Calculate the time between agent assignment and first agent message.
    Returns 0 if no agent message exists or if there's no assignment time.
    """
    if not room.first_user_assigned_at:
        return 0

    first_agent_message = room.messages.filter(
        user__isnull=False,
        created_on__gte=room.first_user_assigned_at
    ).order_by("created_on").first()

    if not first_agent_message:
        return 0

    response_duration = first_agent_message.created_on - room.first_user_assigned_at
    return int(response_duration.total_seconds())
>>>>>>> feature/first-response-metric
