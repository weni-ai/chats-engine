from typing import TYPE_CHECKING
from datetime import timedelta

from django.db.models import Q


if TYPE_CHECKING:
    from django.db.models import QuerySet
    from chats.apps.msgs.models import Message
    from chats.apps.rooms.models import Room


def calculate_response_time(room: "Room") -> int:
    """
    Calculate the average response time for a room.
    """
    messages: QuerySet["Message"] = room.messages.filter(
        Q(user__isnull=False) | Q(contact__isnull=False)
    ).order_by("created_on")

    if not messages.exists():
        return 0

    total_response_time_sum = timedelta(0)
    agent_responses_count = 0

    last_contact_message = None
    last_message_was_from_agent = False

    for message in messages:
        if message.contact:
            last_contact_message = message
            last_message_was_from_agent = False
            continue

        if message.user:
            if last_message_was_from_agent:
                continue

            last_message_was_from_agent = True

            if last_contact_message:
                response_duration = message.created_on - last_contact_message.created_on
                total_response_time_sum += response_duration
                agent_responses_count += 1

    if agent_responses_count == 0:
        return 0

    average_response_seconds = (
        total_response_time_sum.total_seconds() / agent_responses_count
    )
    return int(average_response_seconds)
