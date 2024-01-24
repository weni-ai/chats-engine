import uuid
from typing import List

from rest_framework.authtoken.models import Token

from chats.apps.accounts.models import User
from chats.apps.api.v1.dashboard.dto import RoomData
from chats.apps.api.v1.dashboard.serializers import DashboardRoomSerializer
from chats.apps.contacts.models import Contact
from chats.apps.msgs.models import Message as ChatMessage


def create_user_and_token(nickname: str = "fake"):
    user = User.objects.get_or_create(email=f"{nickname}@user.com")[0]
    token, create = Token.objects.get_or_create(user=user)
    return (user, token)


def create_message(text, room, user=None, contact=None):
    if user == contact:
        return None
    return ChatMessage.objects.create(room=room, text=text, user=user, contact=contact)


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
