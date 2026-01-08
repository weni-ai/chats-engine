from django.db import IntegrityError
from rest_framework.test import APITestCase

from chats.apps.contacts.models import Contact
from chats.apps.projects.models import Project


class ConstraintTests(APITestCase):
    def test_unique_contact_external_id_constraint(self):
        Contact.objects.create(external_id="test-external-id", name="Contact 1")
        with self.assertRaises(IntegrityError) as context:
            Contact.objects.create(external_id="test-external-id", name="Contact 2")
        self.assertIn("unique_contact_external_id", str(context.exception))

    def test_allows_multiple_contacts_with_null_external_id(self):
        Contact.objects.create(external_id=None, name="Contact 1")
        Contact.objects.create(external_id=None, name="Contact 2")
        self.assertEqual(Contact.objects.filter(external_id__isnull=True).count(), 2)


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
