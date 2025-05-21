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
    user_request = User.objects.get(email=user_request)

    if room.user:
        return room.user
    return user_request


def ensure_timezone(dt, tz):
    if dt.tzinfo is None:
        try:
            return tz.localize(dt)
        except AttributeError:
            return dt.replace(tzinfo=tz)
    return dt

def calculate_in_service_time(custom_status_list):
    total = 0
    now = timezone.now()
    for status in custom_status_list or []:
        if status["status_type"] == "In-Service":
            if status["is_active"]:
                created_on = status.get("created_on")
                if created_on:
                    created_on_dt = parse_datetime(created_on)
                    if created_on_dt:
                        total += int((now - created_on_dt).total_seconds())
            else:
                total += status.get("break_time", 0)
    return total

def create_reply_index(message: Message):
    if not message.metadata:
        return

    context = message.metadata.get("context", {})
    if not context:
        return

    replied_external_id = context.get("id")
    if not replied_external_id:
        return

    ChatMessageReplyIndex.objects.update_or_create(
        external_id=replied_external_id,
        message=message,
    )
