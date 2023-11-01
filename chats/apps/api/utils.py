import json
import uuid

from rest_framework.authtoken.models import Token

from chats.apps.accounts.models import User
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


def extract_templating_values(json_data):
    templating_values = []

    flows = json_data.get("flows", [])
    for flow in flows:
        nodes = flow.get("nodes", [])
        for node in nodes:
            actions = node.get("actions", [])
            for action in actions:
                templating_info = action.get("templating", {})
                if "variables" in templating_info and templating_info["variables"]:
                    templating_values.append(templating_info)
    return {"template_infos": templating_values}
