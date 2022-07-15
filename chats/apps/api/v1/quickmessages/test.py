from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from chats.apps.api.utils import create_user_and_token
from chats.apps.api.v1.quickmessages.serializers import QuickMessageSerializer
from chats.apps.quickmessages.models import QuickMessage


class ViewsetTests(APITestCase):
    client = APIClient()
    user = None

    def setUp(self):
        self.user, token = create_user_and_token()
        self.client.credentials(HTTP_AUTHORIZATION="Token " + token.key)

    def create_quick_message(
        self, shortcut: str = "test", text: str = "This is a test quick message"
    ):
        q = QuickMessage.objects.create(
            shortcut=shortcut, text=text, user_id=self.user.id
        )
        return q

    def test_create_quick_message(self):
        """
        Ensure we can create a new quick message.
        """
        url = reverse("quickmessage-list")
        data = {"shortcut": "test", "text": "This is a test quick message"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(QuickMessage.objects.count(), 1)
        self.assertEqual(QuickMessage.objects.get().shortcut, data["shortcut"])
        self.assertEqual(QuickMessage.objects.get().text, data["text"])

    def test_list_quick_messages(self):
        """
        Ensure we can list all user's quick messages.
        """
        quick_messages_count = 3
        for x in range(quick_messages_count):
            self.create_quick_message()

        url = reverse("quickmessage-list")
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(QuickMessage.objects.count(), quick_messages_count)

    def test_retrieve_quick_message(self):
        """
        Ensure we can retrieve a quick message.
        """
        q = self.create_quick_message()
        url = reverse("quickmessage-detail", kwargs={"pk": q.id})
        response = self.client.get(url, format="json")
        data = response.data

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(data["id"], q.id)
        self.assertEqual(data["shortcut"], q.shortcut)
        self.assertEqual(data["text"], q.text)

    def test_update_quick_message(self):
        """
        Ensure we can update a quick message.
        """
        q = self.create_quick_message()
        url = reverse("quickmessage-detail", kwargs={"pk": q.id})
        request_body = {
            "text": "another quick message text",
            "shortcut": "another-shortcut",
        }

        response = self.client.put(url, data=request_body, format="json")
        data = response.data
        q.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(data["id"], q.id)
        self.assertEqual(request_body["shortcut"], q.shortcut)
        self.assertEqual(request_body["text"], q.text)

    def test_delete_quick_message(self):
        """
        Ensure we can delete a quick message.
        """
        q = self.create_quick_message()
        url = reverse("quickmessage-detail", kwargs={"pk": q.id})
        response = self.client.delete(url)
        q = QuickMessage.objects.filter(id=q.id).first()
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertTrue(q is None)

    def test_return_for_not_found_endpoints(self):
        """
        Ensure we get 404_NOT_FOUND HTTP error code for not found endpoints
        """
        detail_url = reverse("quickmessage-detail", kwargs={"pk": 1})

        read = self.client.get(detail_url)
        update = self.client.put(detail_url)
        delete = self.client.delete(detail_url)

        actions = [read, update, delete]

        for action in actions:
            self.assertEqual(action.status_code, status.HTTP_404_NOT_FOUND)


class SerializerTests(APITestCase):
    def test_correct_quick_message_serialization(self):
        """
        Ensure we can serialize a quick message when passed correct data
        """
        data = {"text": "This is a test quick message", "shortcut": "test"}
        serializer = QuickMessageSerializer(data=data)
        is_valid = serializer.is_valid()
        quick_message = serializer.validated_data

        self.assertTrue(is_valid)
        self.assertEqual(quick_message["text"], data["text"])
        self.assertEqual(quick_message["shortcut"], data["shortcut"])

    def test_detect_invalid_data(self):
        """
        Ensure we can detect invalid data on serialize
        """
        data = [
            {"text": "", "shortcut": ""},
            {"text": None, "shortcut": None},
            {},
        ]

        for d in data:
            serializer = QuickMessageSerializer(data=d)
            self.assertFalse(serializer.is_valid())
