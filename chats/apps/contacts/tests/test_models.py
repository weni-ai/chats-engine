from django.test import TestCase
from rest_framework.test import APITestCase

from chats.apps.contacts.models import Contact, normalize_document
from chats.apps.projects.models import Project


class PropertyTests(APITestCase):
    fixtures = ["chats/fixtures/fixture_sector.json"]

    def setUp(self):
        self.contact = Contact.objects.get(uuid="e0dd0853-8192-4ccd-808d-d4b0b32cdee3")
        self.project = Project.objects.get(uuid="34a93b52-231e-11ed-861d-0242ac120002")

    def test_name_property(self):
        """
        Verify if the property for get contact name its returning the correct value.
        """
        self.assertEqual(self.contact.__str__(), self.contact.name)

    def test_full_name(self):
        """
        Verify if the property for get full name its returning the correct value.
        """
        self.assertEqual(self.contact.full_name, self.contact.name)

    def test_linked_user(self):
        self.assertFalse(self.contact.get_linked_user(self.project), self.contact)


class NormalizeDocumentTests(TestCase):
    def test_strips_punctuation(self):
        self.assertEqual(normalize_document("123.456.789-00"), "12345678900")

    def test_strips_spaces(self):
        self.assertEqual(normalize_document("123 456 789 00"), "12345678900")

    def test_strips_mixed_formatting(self):
        self.assertEqual(normalize_document("123-456.789 00"), "12345678900")

    def test_uppercases_letters(self):
        self.assertEqual(normalize_document("ab123cd"), "AB123CD")

    def test_preserves_already_normalized(self):
        self.assertEqual(normalize_document("12345678900"), "12345678900")

    def test_returns_none_for_none(self):
        self.assertIsNone(normalize_document(None))

    def test_returns_empty_for_empty_string(self):
        self.assertEqual(normalize_document(""), "")

    def test_returns_empty_when_only_punctuation(self):
        self.assertEqual(normalize_document("---...   "), "")


class ContactDocumentSaveTests(TestCase):
    def test_save_normalizes_document_with_punctuation(self):
        contact = Contact.objects.create(name="John", document="123.456.789-00")
        contact.refresh_from_db()
        self.assertEqual(contact.document, "12345678900")

    def test_save_normalizes_document_with_spaces(self):
        contact = Contact.objects.create(name="John", document="123 4")
        contact.refresh_from_db()
        self.assertEqual(contact.document, "1234")

    def test_save_uppercases_letters(self):
        contact = Contact.objects.create(name="Maria", document="ab-12cd")
        contact.refresh_from_db()
        self.assertEqual(contact.document, "AB12CD")

    def test_save_keeps_none_when_document_is_none(self):
        contact = Contact.objects.create(name="John", document=None)
        contact.refresh_from_db()
        self.assertIsNone(contact.document)

    def test_save_keeps_empty_when_document_is_empty(self):
        contact = Contact.objects.create(name="John", document="")
        contact.refresh_from_db()
        self.assertEqual(contact.document, "")

    def test_update_or_create_normalizes_document(self):
        """
        Simulates the flow used by RoomFlowSerializer.update_or_create_contact:
        if three room-opening payloads arrive with the document formatted
        differently, the stored value ends up identical on all of them.
        """
        for formatted in ("123-4", "1234", "123 4"):
            Contact.objects.update_or_create(
                external_id="ext-1",
                defaults={"name": "Joao", "document": formatted},
            )

        contact = Contact.objects.get(external_id="ext-1")
        self.assertEqual(contact.document, "1234")
