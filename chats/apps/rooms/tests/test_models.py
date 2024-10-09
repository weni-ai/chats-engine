from unittest.mock import patch

from django.conf import settings
from django.db import IntegrityError
from django.db.utils import DatabaseError
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.rooms.models import Room


class ConstraintTests(APITestCase):
    fixtures = ["chats/fixtures/fixture_sector.json"]

    def setUp(self):
        self.room = Room.objects.get(uuid="090da6d1-959e-4dea-994a-41bf0d38ba26")

    def test_unique_contact_queue_is_activetrue_room_constraint(self):
        with self.assertRaises(IntegrityError) as context:
            Room.objects.create(contact=self.room.contact, queue=self.room.queue)
        self.assertTrue(
            'duplicate key value violates unique constraint "unique_contact_queue_is_activetrue_room"'
            in str(context.exception)
        )


class RetryCloseRoomTests(APITestCase):
    fixtures = ["chats/fixtures/fixture_sector.json"]

    def setUp(self) -> None:
        self.room = Room.objects.get(uuid="090da6d1-959e-4dea-994a-41bf0d38ba26")
        self.agent_token = "8c60c164-32bc-11ed-a261-0242ac120002"

    def _close_room(self, token: str, data: dict):
        url = f"/v1/room/{self.room.uuid}/close/"
        client = self.client
        client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        return client.patch(url, data=data, format="json")

    def test_atomic_transaction_rollback(self):
        """
        Ensure that the database is rolled back if an
        exception occurs during the transaction and that
        no changes are committed.
        """
        instance = self.room
        with patch("chats.apps.rooms.models.Room.close", side_effect=DatabaseError):
            response = self._close_room(self.agent_token, data={})

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

        instance.refresh_from_db()
        self.assertTrue(instance.is_active)
        self.assertIsNone(instance.ended_at)

    def test_atomic_transaction_retries_on_database_error(self):
        """
        Verify that the transaction is retried up to
        MAX_RETRIES times when a DatabaseError occurs.
        """
        with patch(
            "chats.apps.rooms.models.Room.close", side_effect=DatabaseError
        ) as mock_close:
            response = self._close_room(self.agent_token, data={})

        assert mock_close.call_count == settings.MAX_RETRIES
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @patch("chats.apps.rooms.models.Room.request_callback")
    @patch("chats.apps.rooms.models.Room.close")
    def test_atomic_transaction_succeeds_after_retry(
        self, mock_close, mock_request_callback
    ):
        """
        Simulate a DatabaseError on the first attempt,
        but allow the transaction to succeed on subsequent retries.
        """
        instance = self.room
        mock_request_callback.return_value = None

        instance.ended_at = timezone.now()
        instance.is_active = False
        instance.save()

        mock_close.side_effect = [DatabaseError, None]

        response = self._close_room(self.agent_token, data={})

        assert response.status_code == status.HTTP_200_OK

        instance.refresh_from_db()
        assert mock_close.call_count == 2
        assert not instance.is_active
        assert instance.ended_at is not None
