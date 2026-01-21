from unittest.mock import patch

from django.test import TestCase

from chats.apps.accounts.models import User
from chats.apps.api.utils import verify_user_room


class DummyRoom:
    def __init__(self, user=None):
        self.user = user


class VerifyUserRoomTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(email="agent@acme.com")

    def test_returns_existing_room_user(self):
        room = DummyRoom(user=self.user)
        self.assertEqual(verify_user_room(room, "ignored"), self.user)

    @patch("chats.core.cache_utils.get_user_id_by_email_cached")
    def test_resolves_user_from_email(self, mock_cache):
        mock_cache.return_value = self.user.pk
        room = DummyRoom(user=None)
        resolved = verify_user_room(room, "Agent@Acme.com")
        self.assertEqual(resolved, self.user)

    @patch("chats.core.cache_utils.get_user_id_by_email_cached", return_value=None)
    def test_raises_when_email_not_found(self, _):
        room = DummyRoom(user=None)
        with self.assertRaises(User.DoesNotExist):
            verify_user_room(room, "x@acme.com")
