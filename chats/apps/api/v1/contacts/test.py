from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from chats.apps.api.utils import create_user_and_token
from chats.apps.api.v1.contacts.serializers import ContactSerializer
from chats.apps.contacts.models import Contact


class TestContactsViewsets(APITestCase):
    client = APIClient()
    user = None

    def setUp(self):
        self.user, token = create_user_and_token()
        self.client.credentials(HTTP_AUTHORIZATION="Token " + token.key)

    def create_contact(
        self, name: str = "João da Silva", email="joao.da.silva@email.com"
    ):
        c = Contact.objects.create(name=name, email=email)
        return c

    def test_list_contacts(self):
        """
        Ensure we can list all contacts
        """
        self.create_contact()
        self.create_contact(email="joaodasilva@email.com")

        url = reverse("contact-list")
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Contact.objects.count(), 2)

    def test_retrieve_contact(self):
        """
        Ensure we can retrieve a contact
        """
        c = self.create_contact()

        url = reverse("contact-detail", kwargs={"pk": c.id})
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], c.id)

    def test_handling_not_allowed_http_methods(self):
        url = reverse("contact-detail", kwargs={"pk": 1})
        post = self.client.post(url, format="json")
        put = self.client.put(url, format="json")
        delete = self.client.delete(url, format="json")
        actions = [post, put, delete]

        for action in actions:
            self.assertEqual(action.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class TestContactSerializer(APITestCase):
    def test_correct_contact_serialization(self):
        """
        Ensure we can serialize a contact when passed correct data
        """
        data = {"email": "test@email.com", "name": "Test Contact"}
        serializer = ContactSerializer(data=data)
        is_valid = serializer.is_valid()
        contact = serializer.validated_data

        self.assertTrue(is_valid)
        self.assertEqual(contact["email"], data["email"])
        self.assertEqual(contact["name"], data["name"])

    def test_detect_invalid_data(self):
        """
        Ensure we can detect invalid data on serialize
        """
        data = [
            {"name": "", "email": ""},
            {"name": None, "email": None},
            {},
        ]

        for d in data:
            serializer = ContactSerializer(data=d)
            self.assertFalse(serializer.is_valid())
