from django.test import TestCase

from chats.apps.contacts.models import Contact
from chats.apps.contacts.usecases.fill_contact_from_custom_fields import (
    get_contact_updates_from_custom_fields,
)


class GetContactUpdatesFromCustomFieldsTests(TestCase):
    def test_fills_empty_email_and_document(self):
        contact = Contact(email="", document="")
        updates = get_contact_updates_from_custom_fields(
            contact, {"email": "qa01@weni.ai", "document": "111.222.333-44"}
        )

        self.assertEqual(updates["email"], "qa01@weni.ai")
        self.assertEqual(updates["document"], "11122233344")

    def test_does_not_overwrite_existing_contact_fields(self):
        contact = Contact(email="contact@weni.ai", document="99988877766")
        updates = get_contact_updates_from_custom_fields(
            contact, {"email": "qa01@weni.ai", "document": "111.222.333-44"}
        )

        self.assertEqual(updates, {})

    def test_fills_only_empty_fields(self):
        contact = Contact(email="contact@weni.ai", document="")
        updates = get_contact_updates_from_custom_fields(
            contact, {"email": "qa01@weni.ai", "document": "111.222.333-44"}
        )

        self.assertEqual(updates, {"document": "11122233344"})

    def test_ignores_non_dict_custom_fields(self):
        contact = Contact(email="", document="")
        self.assertEqual(get_contact_updates_from_custom_fields(contact, None), {})
        self.assertEqual(get_contact_updates_from_custom_fields(contact, ["email"]), {})

    def test_ignores_non_string_and_blank_values(self):
        contact = Contact(email="", document="")
        updates = get_contact_updates_from_custom_fields(
            contact,
            {"email": 123, "document": "   "},
        )

        self.assertEqual(updates, {})
