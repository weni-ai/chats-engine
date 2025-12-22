import logging
import uuid
from typing import List

from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.authtoken.models import Token

from chats.apps.accounts.models import User
from chats.apps.api.v1.dashboard.dto import RoomData
from chats.apps.api.v1.dashboard.serializers import DashboardRoomSerializer
from chats.apps.contacts.models import Contact
from chats.apps.msgs.models import ChatMessageReplyIndex, Message

logger = logging.getLogger(__name__)


def create_user_and_token(nickname: str = "fake"):
    user = User.objects.get_or_create(email=f"{nickname}@user.com")[0]
    token, create = Token.objects.get_or_create(user=user)
    return (user, token)


def create_message(text, room, user=None, contact=None):
    if user == contact:
        return None
    return Message.objects.create(room=room, text=text, user=user, contact=contact)


def create_contact(
    name: str, email: str, status: str = "OFFLINE", custom_fields: dict = {}
):
    return Contact.objects.create(
        name=name,
        email=email,
        status=status,
        custom_fields=custom_fields,
        external_id=str(uuid.uuid4()),
    )


def create_room_dto(rooms_data) -> List[DashboardRoomSerializer]:
    room_data = [
        RoomData(
            interact_time=rooms_data.get("interact_time", None),
            response_time=rooms_data.get("response_time", None),
            waiting_time=rooms_data.get("waiting_time", None),
        )
    ]
    serialized_data = DashboardRoomSerializer(room_data, many=True)
    return serialized_data.data


def verify_user_room(room, user_request):
    from chats.apps.accounts.models import User
    from chats.core.cache_utils import get_user_id_by_email_cached

    if room.user:
        return room.user

    if isinstance(user_request, str):
        uid = get_user_id_by_email_cached(user_request)
        if uid is None:
            raise User.DoesNotExist()
        return User.objects.get(pk=uid)
    return user_request


def ensure_timezone(dt, tz):
    if dt.tzinfo is None:
        try:
            return tz.localize(dt)
        except AttributeError:
            return dt.replace(tzinfo=tz)
    return dt


def create_reply_index(message: Message):
    if not message.external_id:
        return

    if ChatMessageReplyIndex.objects.filter(external_id=message.external_id).exists():
        ChatMessageReplyIndex.objects.filter(external_id=message.external_id).update(
            message=message,
        )
    else:
        ChatMessageReplyIndex.objects.update_or_create(
            external_id=message.external_id,
            message=message,
        )


def calculate_in_service_time(custom_status_list, user_status=None):
    total = 0
    current_tz = timezone.get_current_timezone()
    now = timezone.now()

    logger.debug(f"Calculating in-service time at {now}")

    for status in custom_status_list or []:
        if status["status_type"] == "In-Service":
            if status["is_active"] and user_status == "ONLINE":
                created_on = status.get("created_on")
                if created_on:
                    created_on_dt = parse_datetime(created_on)
                    if created_on_dt:
                        created_on_dt = ensure_timezone(created_on_dt, current_tz)
                        now_tz = ensure_timezone(now, current_tz)
                        period = int((now_tz - created_on_dt).total_seconds())
                        logger.debug(
                            f"Live active period: {period} seconds (from {created_on_dt} to {now_tz})"
                        )
                        total += period
            elif not status["is_active"]:
                break_time = status.get("break_time", 0)
                logger.debug(f"Accumulated break time: {break_time} seconds")
                total += break_time

    logger.debug(f"Total in-service time: {total} seconds")
    return total
