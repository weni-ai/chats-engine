import json

from rest_framework.authtoken.models import Token

from chats.apps.accounts.models import User
from chats.apps.msgs.models import Message as ChatMessage
from chats.apps.contacts.models import Contact


def create_user_and_token(nickname: str = "fake"):
    user = User.objects.create_user("{}@user.com".format(nickname), nickname)
    token, create = Token.objects.get_or_create(user=user)
    return (user, token)


def create_message(text, room, user=None, contact=None):
    if user == contact:
        return None
    return ChatMessage.objects.create(room=room, text=text, user=user, contact=contact)


def create_contact(name: str, email: str, status: str, custom_fields: dict):
    return Contact.objects.create(
        name=name, email=email, status=status, custom_fields=custom_fields
    )
