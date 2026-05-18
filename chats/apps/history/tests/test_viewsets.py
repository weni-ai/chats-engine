from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from django.core.files.uploadedfile import SimpleUploadedFile
from chats.apps.archive_chats.choices import ArchiveConversationsJobStatus
from chats.apps.archive_chats.models import (
    ArchiveConversationsJob,
    RoomArchivedConversation,
)
from chats.core.tests.test_base import BaseAPIChatsTestCase


class TestHistoryRoomViewsets(BaseAPIChatsTestCase):
    def _list_request(self, token, data):
        url = reverse("history_room-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + token.key)
        response = client.get(url, format="json", data=data)
        results = response.json().get("results")
        return response, results

    def test_admin_list_within_its_project(self):
        payload = {"project": str(self.project.uuid)}
        self.deactivate_rooms()
        response = self._list_request(token=self.admin_token, data=payload)[0]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("count"), self.count_project_1_contact)

    def test_manager_list_within_its_sectors(self):
        payload = {"project": str(self.project.uuid)}
        self.deactivate_rooms()
        response = self._list_request(token=self.manager_token, data=payload)[0]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("count"), 3)

    def test_agent_list_within_its_rooms(self):
        payload = {"project": str(self.project.uuid)}
        self.deactivate_rooms()
        response, _ = self._list_request(token=self.agent_token, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("count"), 2)

    def test_basic_list(self):
        payload = {
            "project": str(self.project.uuid),
            "basic": True,
            "contact": self.contact.external_id,
        }
        self.deactivate_rooms()
        response = self._list_request(token=self.admin_token, data=payload)[0]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("count"), 1)
        self.assertEqual(len(response.json().get("results")[0]), 2)

    def test_admin_list_with_blocked_contacts(self):
        self.project.add_contact_to_history_blocklist(self.contact_2.external_id)

        payload = {"project": str(self.project.uuid)}
        self.deactivate_rooms()
        response = self._list_request(token=self.admin_token, data=payload)[0]

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("count"), self.count_project_1_contact - 1)

    def test_retrieve_room_ok(self):
        """
        Ensure we can retrieve a contact
        """
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.admin_token.key)
        self.contact.rooms.update(is_active=False, ended_at=timezone.now())
        url = (
            reverse("history_room-detail", kwargs={"pk": str(self.room_1.pk)})
            + f"?project={str(self.project.uuid)}"
        )
        response = client.get(
            url,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data.get("is_archived"))
        self.assertIsNone(response.data.get("archived_conversation_file_url"))

    def test_retrieve_room_ok_with_archived_conversation(self):
        """
        Ensure we can retrieve a room with an archived conversation
        """
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.admin_token.key)

        RoomArchivedConversation.objects.create(
            job=ArchiveConversationsJob.objects.create(started_at=timezone.now()),
            room=self.room_1,
            file=SimpleUploadedFile(
                "test.zip", b"test", content_type="application/zip"
            ),
            status=ArchiveConversationsJobStatus.FINISHED,
        )

        self.contact.rooms.update(is_active=False, ended_at=timezone.now())

        url = (
            reverse("history_room-detail", kwargs={"pk": str(self.room_1.pk)})
            + f"?project={str(self.project.uuid)}"
        )
        response = client.get(
            url,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get("is_archived"))
        self.assertIsNotNone(response.data.get("archived_conversation_file_url"))

    def test_retrieve_contact_no_closed_rooms(self):
        """
        Ensure we can retrieve a contact
        """
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.admin_token.key)
        url = (
            reverse("history_room-detail", kwargs={"pk": str(self.room_1.pk)})
            + f"?project={str(self.project.uuid)}"
        )
        response = self.client.get(
            url,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_contact_unauthorized(self):
        """
        Ensure we can retrieve a contact
        """
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.agent_token.key)
        self.contact_2.rooms.update(is_active=False, ended_at=timezone.now())
        url = (
            reverse("history_room-detail", kwargs={"pk": str(self.room_2.pk)})
            + f"?project={str(self.project.uuid)}"
        )
        response = client.get(url, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_handling_not_allowed_http_methods(self):
        url = reverse("history_room-detail", kwargs={"pk": 1})
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.admin_token.key)
        post = client.post(url, format="json")
        put = client.put(url, format="json")
        delete = client.delete(url, format="json")
        actions = [post, put, delete]

        for action in actions:
            self.assertEqual(action.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class TestHistoryRoomSearchFields(BaseAPIChatsTestCase):
    """
    Validates that `HistoryRoomViewset.search_fields` accepts
    contact email/document and that document lookups ignore punctuation.
    """

    def _search(self, term):
        url = reverse("history_room-list")
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.admin_token.key)
        return self.client.get(
            url,
            format="json",
            data={"project": str(self.project.uuid), "search": term},
        )

    def setUp(self):
        super().setUp()
        self.deactivate_rooms()

        self.contact.email = "john.doe@tokstok.com"
        self.contact.document = "123.456.789-00"
        self.contact.save()

        self.contact_2.email = "mary@example.com"
        self.contact_2.document = "98765432100"
        self.contact_2.save()

    def test_search_by_contact_email(self):
        response = self._search("john.doe@tokstok.com")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        uuids = [r["uuid"] for r in response.json()["results"]]
        self.assertIn(str(self.room_1.uuid), uuids)
        self.assertNotIn(str(self.room_2.uuid), uuids)

    def test_search_by_contact_document_without_formatting(self):
        response = self._search("12345678900")
        uuids = [r["uuid"] for r in response.json()["results"]]
        self.assertIn(str(self.room_1.uuid), uuids)
        self.assertNotIn(str(self.room_2.uuid), uuids)

    def test_search_by_contact_document_with_dashes(self):
        response = self._search("123-456-789-00")
        uuids = [r["uuid"] for r in response.json()["results"]]
        self.assertIn(str(self.room_1.uuid), uuids)

    def test_search_by_contact_document_with_dots(self):
        response = self._search("123.456.789.00")
        uuids = [r["uuid"] for r in response.json()["results"]]
        self.assertIn(str(self.room_1.uuid), uuids)

    def test_search_by_contact_document_with_spaces(self):
        response = self._search("123 456 789 00")
        uuids = [r["uuid"] for r in response.json()["results"]]
        self.assertIn(str(self.room_1.uuid), uuids)

    def test_search_by_contact_name_still_works(self):
        response = self._search(self.contact.name)
        uuids = [r["uuid"] for r in response.json()["results"]]
        self.assertIn(str(self.room_1.uuid), uuids)

    def test_search_with_unrelated_term_returns_empty(self):
        response = self._search("notfound-xyz-9999")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("count"), 0)


class TestHistoryRoomContactFilterUnification(BaseAPIChatsTestCase):
    """
    Validates the epic requirement: `GET /history?contact=<external_id>`
    must return rooms from any Contact that shares email or document
    with the contact identified by the external_id.
    """

    def _list(self, contact_external_id):
        url = reverse("history_room-list")
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.admin_token.key)
        return self.client.get(
            url,
            format="json",
            data={
                "project": str(self.project.uuid),
                "contact": contact_external_id,
            },
        )

    def setUp(self):
        super().setUp()
        self.deactivate_rooms()

    def test_unifies_history_by_document(self):
        """
        Simulates the web chat scenario: two sessions of the same person
        (same document, different URN/external_id).
        """
        self.contact.external_id = "ws-001"
        self.contact.document = "12345678900"
        self.contact.save()

        self.contact_2.external_id = "ws-002"
        self.contact_2.document = "123.456.789-00"  # same CPF, different format
        self.contact_2.queue = self.queue_1  # ensure admin can see it
        self.contact_2.save()

        # rooms already exist from BaseAPIChatsTestCase; deactivate_rooms()
        # closed them, and both rooms belong to the admin's project
        response = self._list("ws-002")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        uuids = [r["uuid"] for r in response.json()["results"]]
        self.assertIn(str(self.room_1.uuid), uuids)
        self.assertIn(str(self.room_2.uuid), uuids)

    def test_unifies_history_by_email(self):
        self.contact.external_id = "ws-001"
        self.contact.email = "joao@tokstok.com"
        self.contact.save()

        self.contact_2.external_id = "ws-002"
        self.contact_2.email = "joao@tokstok.com"
        self.contact_2.save()

        response = self._list("ws-002")

        uuids = [r["uuid"] for r in response.json()["results"]]
        self.assertIn(str(self.room_1.uuid), uuids)
        self.assertIn(str(self.room_2.uuid), uuids)

    def test_does_not_unify_when_email_and_document_differ(self):
        self.contact.external_id = "ws-001"
        self.contact.email = "a@x.com"
        self.contact.document = "111"
        self.contact.save()

        self.contact_2.external_id = "ws-002"
        self.contact_2.email = "b@x.com"
        self.contact_2.document = "222"
        self.contact_2.save()

        response = self._list("ws-002")

        uuids = [r["uuid"] for r in response.json()["results"]]
        self.assertIn(str(self.room_2.uuid), uuids)
        self.assertNotIn(str(self.room_1.uuid), uuids)

    def test_falls_back_to_external_id_when_contact_not_found(self):
        """
        When the external_id does not match any Contact, keep the legacy
        behavior of filtering by `contact__external_id`.
        """
        response = self._list("does-not-exist")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("count"), 0)


class TestHistoryRoomIdentifierFilters(BaseAPIChatsTestCase):
    """
    Validates the `?contact=`, `?email=` and `?document=` filters used by
    the "Ver histórico" button. The frontend sends whichever identifiers
    are available on the current room's contact and the backend unifies
    history across every Contact that matches any of them.
    """

    def _list(self, **params):
        url = reverse("history_room-list")
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.admin_token.key)
        data = {"project": str(self.project.uuid)}
        data.update(params)
        return self.client.get(url, format="json", data=data)

    def setUp(self):
        super().setUp()
        self.deactivate_rooms()

    def _set_contacts(
        self,
        *,
        c1_external_id=None,
        c1_email=None,
        c1_document=None,
        c2_external_id=None,
        c2_email=None,
        c2_document=None,
    ):
        if c1_external_id is not None:
            self.contact.external_id = c1_external_id
        if c1_email is not None:
            self.contact.email = c1_email
        if c1_document is not None:
            self.contact.document = c1_document
        self.contact.save()

        if c2_external_id is not None:
            self.contact_2.external_id = c2_external_id
        if c2_email is not None:
            self.contact_2.email = c2_email
        if c2_document is not None:
            self.contact_2.document = c2_document
        self.contact_2.save()

    def _uuids(self, response):
        return [r["uuid"] for r in response.json()["results"]]

    def test_email_only_unifies_history(self):
        """Scenario: WhatsApp + Telegram users with same email."""
        self._set_contacts(
            c1_external_id="wpp-001",
            c1_email="kallil@gmail.com",
            c2_external_id="tg-002",
            c2_email="kallil@gmail.com",
        )

        response = self._list(email="kallil@gmail.com")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        uuids = self._uuids(response)
        self.assertIn(str(self.room_1.uuid), uuids)
        self.assertIn(str(self.room_2.uuid), uuids)

    def test_email_match_is_case_insensitive(self):
        self._set_contacts(
            c1_email="kallil@gmail.com",
            c2_email="kallil@gmail.com",
        )

        response = self._list(email="KALLIL@Gmail.COM")

        uuids = self._uuids(response)
        self.assertIn(str(self.room_1.uuid), uuids)
        self.assertIn(str(self.room_2.uuid), uuids)

    def test_document_only_unifies_history(self):
        self._set_contacts(
            c1_external_id="wpp-001",
            c1_document="12345678900",
            c2_external_id="tg-002",
            c2_document="123.456.789-00",
        )

        response = self._list(document="12345678900")

        uuids = self._uuids(response)
        self.assertIn(str(self.room_1.uuid), uuids)
        self.assertIn(str(self.room_2.uuid), uuids)

    def test_document_ignores_punctuation_in_query(self):
        self._set_contacts(
            c1_document="12345678900",
            c2_document="12345678900",
        )

        response = self._list(document="123.456.789-00")

        uuids = self._uuids(response)
        self.assertIn(str(self.room_1.uuid), uuids)
        self.assertIn(str(self.room_2.uuid), uuids)

    def test_contact_and_email_combined_returns_union(self):
        """
        Sends both the original external_id (WhatsApp) and an email shared
        with another Contact (Telegram). Both rooms should come back even
        though no single identifier covers both Contacts on its own.
        """
        self._set_contacts(
            c1_external_id="wpp-001",
            c1_email="kallil@gmail.com",
            c2_external_id="tg-002",
            c2_email="kallil@gmail.com",
        )

        response = self._list(contact="wpp-001", email="kallil@gmail.com")

        uuids = self._uuids(response)
        self.assertIn(str(self.room_1.uuid), uuids)
        self.assertIn(str(self.room_2.uuid), uuids)

    def test_all_three_identifiers_combined(self):
        self._set_contacts(
            c1_external_id="wpp-001",
            c1_email="kallil@gmail.com",
            c1_document="12345678900",
            c2_external_id="tg-002",
            c2_email="kallil@gmail.com",
            c2_document="98765432100",
        )

        response = self._list(
            contact="wpp-001",
            email="kallil@gmail.com",
            document="12345678900",
        )

        uuids = self._uuids(response)
        self.assertIn(str(self.room_1.uuid), uuids)
        self.assertIn(str(self.room_2.uuid), uuids)

    def test_email_only_does_not_match_other_contacts(self):
        self._set_contacts(
            c1_email="joao@x.com",
            c2_email="maria@x.com",
        )

        response = self._list(email="joao@x.com")

        uuids = self._uuids(response)
        self.assertIn(str(self.room_1.uuid), uuids)
        self.assertNotIn(str(self.room_2.uuid), uuids)

    def test_document_only_does_not_match_other_contacts(self):
        self._set_contacts(
            c1_document="111",
            c2_document="222",
        )

        response = self._list(document="111")

        uuids = self._uuids(response)
        self.assertIn(str(self.room_1.uuid), uuids)
        self.assertNotIn(str(self.room_2.uuid), uuids)

    def test_no_match_for_any_identifier_returns_empty(self):
        response = self._list(
            contact="unknown",
            email="unknown@x.com",
            document="00000000000",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("count"), 0)

    def test_contact_with_email_but_no_document_unifies_via_email(self):
        """
        Contact A has only email, Contact B has the same email but also a
        document. Sending Contact A's external_id should still unify them.
        """
        self._set_contacts(
            c1_external_id="wpp-001",
            c1_email="kallil@gmail.com",
            c1_document="",
            c2_external_id="tg-002",
            c2_email="kallil@gmail.com",
            c2_document="12345678900",
        )

        response = self._list(contact="wpp-001")

        uuids = self._uuids(response)
        self.assertIn(str(self.room_1.uuid), uuids)
        self.assertIn(str(self.room_2.uuid), uuids)

    def test_contact_with_document_but_no_email_unifies_via_document(self):
        self._set_contacts(
            c1_external_id="wpp-001",
            c1_email="",
            c1_document="12345678900",
            c2_external_id="tg-002",
            c2_email="someoneelse@gmail.com",
            c2_document="12345678900",
        )

        response = self._list(contact="wpp-001")

        uuids = self._uuids(response)
        self.assertIn(str(self.room_1.uuid), uuids)
        self.assertIn(str(self.room_2.uuid), uuids)

    def test_combined_with_sector_filter(self):
        """
        Other filters (sector, tag, ended_at) must still apply on top of
        the unified contact set.
        """
        self._set_contacts(
            c1_email="kallil@gmail.com",
            c2_email="kallil@gmail.com",
        )

        response = self._list(
            email="kallil@gmail.com",
            sector=str(self.sector_1.uuid),
        )

        uuids = self._uuids(response)
        self.assertIn(str(self.room_1.uuid), uuids)
        self.assertIn(str(self.room_2.uuid), uuids)
        # room_3 belongs to sector_2 and must be filtered out even if
        # contact_3 shared the email (not the case here, but the assertion
        # documents the intended scoping).
        self.assertNotIn(str(self.room_3.uuid), uuids)

    def test_combined_with_search_filter(self):
        """
        `email` unifies the contact set; `search` then refines within it.
        """
        self._set_contacts(
            c1_email="kallil@gmail.com",
            c2_email="kallil@gmail.com",
        )

        response = self._list(
            email="kallil@gmail.com",
            search=self.contact.name,
        )

        uuids = self._uuids(response)
        self.assertIn(str(self.room_1.uuid), uuids)
        self.assertNotIn(str(self.room_2.uuid), uuids)

    def test_legacy_contact_param_still_unifies(self):
        """Ensures backward compatibility with the existing `?contact=` flow."""
        self._set_contacts(
            c1_external_id="wpp-001",
            c1_email="kallil@gmail.com",
            c2_external_id="tg-002",
            c2_email="kallil@gmail.com",
        )

        response = self._list(contact="wpp-001")

        uuids = self._uuids(response)
        self.assertIn(str(self.room_1.uuid), uuids)
        self.assertIn(str(self.room_2.uuid), uuids)
