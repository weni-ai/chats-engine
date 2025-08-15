from unittest.mock import patch

from django.test import TestCase

from chats.apps.api.v1.msgs.serializers import BaseMessageSerializer
from chats.apps.rooms.models import Room


class BaseMessageSerializerTests(TestCase):
    @patch(
        "chats.apps.api.v1.msgs.serializers.get_user_id_by_email_cached",
        return_value=123,
    )
    def test_validate_sets_user_id_lower(self, _):
        room = Room.objects.create()
        s = BaseMessageSerializer(
            data={"room": room.pk, "user_email": "Agent@Acme.com", "text": "hi"}
        )
        s.is_valid(raise_exception=True)
        self.assertEqual(s.validated_data["user_id"], "agent@acme.com")
