from rest_framework.authtoken.models import Token

from chats.apps.accounts.models import User
from chats.apps.msgs.models import Message as ChatMessage


def create_user_and_token(nickname: str = "fake"):
    user = User.objects.create_user("{}@user.com".format(nickname), nickname)
    token, create = Token.objects.get_or_create(user=user)
    return (user, token)


def create_message(text, room, user=None, contact=None):
    if user == contact:
        return None
    return ChatMessage.objects.create(room=room, text=text, user=user, contact=contact)
