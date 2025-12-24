from unittest import mock

from django.test import override_settings
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils import timezone
from django.utils.timezone import timedelta
from rest_framework import status
from rest_framework.test import APITestCase


from chats.apps.accounts.models import User
from chats.apps.api.utils import create_user_and_token
from chats.apps.msgs.models import Message
from chats.apps.rooms.models import Room


class MsgsExternalTests(APITestCase):
    fixtures = ["chats/fixtures/fixture_app.json"]

    def setUp(self) -> None:
        self.room = Room.objects.get(uuid="090da6d1-959e-4dea-994a-41bf0d38ba26")

    def _remove_user(self):
        room = self.room
        room.user = None
        room.save()
        return room

    def _update_default_message(self, default_message):
        queue = self.room.queue
        queue.default_message = default_message
        queue.save()
        return queue

    def _request_create_message(
        self,
        direction: str = "incoming",
        created_on=None,
        token=None,
        token_type: str = "Bearer",
    ):
        if token is None:
            token = "f3ce543e-d77e-4508-9140-15c95752a380"

        url = reverse("external_message-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION=f"{token_type} {token}")
        data = {
            "room": self.room.uuid,
            "text": "olá.",
            "direction": direction,
            "attachments": [{"content_type": "string", "url": "http://example.com"}],
            "created_on": created_on,
        }
        return client.post(url, data=data, format="json")

    def _request_update_message(
        self, message, data, token=None, token_type: str = "Bearer"
    ):
        if token is None:
            token = "f3ce543e-d77e-4508-9140-15c95752a380"

        url = reverse("external_message-detail", kwargs={"uuid": message.uuid})
        client = self.client
        client.credentials(HTTP_AUTHORIZATION=f"{token_type} {token}")
        return client.patch(url, data=data, format="json")

    def _request_list_messages(self, token=None, token_type: str = "Bearer"):
        if token is None:
            token = "f3ce543e-d77e-4508-9140-15c95752a380"

        url = reverse("external_message-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION=f"{token_type} {token}")
        return client.get(url, {"room": self.room.uuid}, format="json")

    def test_create_external_msgs(self):
        """
        Verify if the external message endpoint are creating messages correctly.
        """
        created_on = timezone.now() - timedelta(days=5)
        response = self._request_create_message(created_on=created_on)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.room.messages.count(), 3)

        msg = Message.objects.filter(uuid=response.data["uuid"]).first()
        self.assertIsNotNone(msg)
        self.assertEqual(msg.created_on, created_on)

    def test_create_external_msgs_with_null_created_on(self):
        """
        Verify if the external message endpoint are creating messages correctly
        when passing a null created_on.
        """
        response = self._request_create_message()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.room.messages.count(), 3)

        msg = Message.objects.filter(uuid=response.data["uuid"]).first()
        self.assertIsNotNone(msg)
        self.assertEqual(msg.created_on.date(), timezone.now().date())

    def test_create_with_default_message_room_without_user(self):
        _ = self._remove_user()

        queue = self._update_default_message(default_message="DEFAULT MESSAGE")

        response = self._request_create_message()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.room.messages.count(), 4)
        self.assertEqual(
            self.room.messages.order_by("-created_on").first().text,
            queue.default_message,
        )

    def test_create_with_default_message_room_with_user(self):
        queue = self._update_default_message(default_message="DEFAULT MESSAGE")

        response = self._request_create_message()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.room.messages.count(), 3)
        self.assertNotEqual(
            self.room.messages.order_by("-created_on").first().text,
            queue.default_message,
        )

    def test_create_without_default_message_room_without_user(self):
        room = self._remove_user()
        response = self._request_create_message()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.room.messages.count(), 3)
        self.assertNotEqual(
            self.room.messages.order_by("-created_on").first().text,
            room.queue.default_message,
        )

    def test_create_without_default_message_room_with_user(self):
        response = self._request_create_message()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.room.messages.count(), 3)
        self.assertNotEqual(
            self.room.messages.order_by("-created_on").first().text,
            self.room.queue.default_message,
        )

    def test_create_with_empty_default_message_room_without_user(self):
        _ = self._remove_user()

        queue = self._update_default_message(default_message="")

        response = self._request_create_message()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.room.messages.count(), 3)
        self.assertNotEqual(
            self.room.messages.order_by("-created_on").first().text,
            queue.default_message,
        )

    def test_create_outgoing_with_default_message_room_without_user(self):
        _ = self._remove_user()

        queue = self._update_default_message(default_message="DEFAULT MESSAGE")

        response = self._request_create_message(direction="outgoing")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.room.messages.count(), 3)
        self.assertNotEqual(
            self.room.messages.order_by("-created_on").first().text,
            queue.default_message,
        )

    @mock.patch(
        "chats.apps.accounts.authentication.drf.backends.WeniOIDCAuthenticationBackend.get_userinfo"
    )
    def test_create_external_msgs_with_internal_token(self, mock_get_userinfo):
        mock_get_userinfo.return_value = {
            "sub": "test_user",
            "email": "test_user@example.com",
        }

        user, token = create_user_and_token("test_user")

        permission, created = Permission.objects.get_or_create(
            codename="can_communicate_internally",
            content_type=ContentType.objects.get_for_model(User),
        )
        user.user_permissions.add(permission)
        self.client.force_authenticate(user)

        response = self._request_create_message(token=token)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @mock.patch(
        "chats.apps.api.v1.internal.permissions.ModuleHasPermission.has_permission",
    )
    def test_cannot_create_external_msgs_with_internal_token_without_can_communicate_internally_perm(
        self, mock_has_permission
    ):
        mock_has_permission.return_value = False
        user, token = create_user_and_token("test_user")
        self.client.force_authenticate(user)

        response = self._request_create_message(token=token)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        mock_has_permission.assert_called_once()

    @override_settings(INTERNAL_API_TOKEN="dummy-token")
    def test_create_external_msgs_with_internal_api_token(self):
        response = self._request_create_message(token="dummy-token", token_type="Token")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @override_settings(INTERNAL_API_TOKEN="dummy-token")
    def test_create_external_msgs_with_internal_api_token_with_invalid_token(self):
        response = self._request_create_message(
            token="invalid-token", token_type="Token"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_external_msgs(self):
        message = self.room.messages.create(
            text="test.",
        )

        data = {
            "text": "updated.",
        }

        response = self._request_update_message(message, data=data)
        message.refresh_from_db(fields=["text"])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(message.text, data.get("text"))

    @mock.patch(
        "chats.apps.accounts.authentication.drf.backends.WeniOIDCAuthenticationBackend.get_userinfo"
    )
    def test_update_external_msgs_with_internal_token(self, mock_get_userinfo):
        mock_get_userinfo.return_value = {
            "sub": "test_user",
            "email": "test_user@example.com",
        }

        message = self.room.messages.create(
            text="test.",
        )

        data = {
            "text": "updated.",
        }

        user, token = create_user_and_token("test_user")

        permission, created = Permission.objects.get_or_create(
            codename="can_communicate_internally",
            content_type=ContentType.objects.get_for_model(User),
        )
        user.user_permissions.add(permission)
        self.client.force_authenticate(user)

        response = self._request_update_message(message, data=data, token=token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @mock.patch(
        "chats.apps.api.v1.internal.permissions.ModuleHasPermission.has_permission",
    )
    def test_cannot_update_external_msgs_with_internal_token_without_can_communicate_internally_perm(
        self, mock_has_permission
    ):
        mock_has_permission.return_value = False
        from django_redis import get_redis_connection

        message = self.room.messages.create(
            text="test.",
        )

        import uuid

        unique_username = f"test_user_no_perm_{uuid.uuid4().hex[:8]}"
        user, token = create_user_and_token(unique_username)

        redis_connection = get_redis_connection()
        cache_key = f"internal_client_perm:{user.id}"
        redis_connection.delete(cache_key)

        self.client.force_authenticate(user)

        response = self._request_update_message(message, data={}, token=token)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        mock_has_permission.assert_called_once()

    def test_list_external_msgs(self):
        response = self._request_list_messages()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_external_msgs_with_internal_token(self):
        user, token = create_user_and_token("test_user")

        permission, created = Permission.objects.get_or_create(
            codename="can_communicate_internally",
            content_type=ContentType.objects.get_for_model(User),
        )
        user.user_permissions.add(permission)
        self.client.force_authenticate(user)

        response = self._request_list_messages(token=token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @mock.patch(
        "chats.apps.api.v1.internal.permissions.ModuleHasPermission.has_permission",
        return_value=False,
    )
    def test_cannot_list_external_msgs_with_internal_token_without_can_communicate_internally_perm(
        self, mock_has_permission
    ):
        mock_has_permission.return_value = False
        user, token = create_user_and_token("test_user")
        self.client.force_authenticate(user)

        response = self._request_list_messages(token=token)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        mock_has_permission.assert_called_once()
