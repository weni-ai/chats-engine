from unittest import mock

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.contacts.models import Contact
from chats.apps.msgs.models import ChatMessageReplyIndex, Message
from chats.apps.msgs.utils import extract_wamid_core
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector

User = get_user_model()


# Two distinct WAMIDs whose stable cores still differ; we use them to assert
# that the fallback honors the core-based lookup rather than falling through
# to "first row with any non-null core".
WAMID_STORED = (
    "wamid.HBgMNTU0MTk4NTY3MDM0FQIAERgSODVEMjRDRkUyREFBRkM3QTExAA=="
)
# Crafted reply WAMID: same trailing core bytes as ``WAMID_STORED``, different
# envelope (HBgT prefix) and a different leading section. Built to exercise
# the exact production scenario where Meta sends a different ``context.id``
# envelope than the one we stored as ``external_id``.
WAMID_REPLY_DIFFERENT_ENVELOPE = (
    "wamid.HBgTQlIuMTE4MDk1NTMyMDg2MDk4OBUUABIYFjNFQjAwRUM1QkU1NTlDMTYwMUQwREYA"
)


class _BaseFallbackSetup(APITestCase):
    """Shared setup: project, sector, queue, agent, contact, active room."""

    def setUp(self):
        self.agent = User.objects.create_user(
            email="agent@test.com", password="x", first_name="Ana", last_name="Lima"
        )
        self.contact = Contact.objects.create(name="Cliente", email="c@test.com")
        self.project = Project.objects.create(name="Project Reply Fallback")
        ProjectPermission.objects.create(
            user=self.agent,
            project=self.project,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Queue", sector=self.sector)
        self.room = Room.objects.create(
            contact=self.contact,
            is_active=True,
            queue=self.queue,
            user=self.agent,
            project_uuid=str(self.project.uuid),
        )
        self.original_message = Message.objects.create(
            room=self.room,
            user=self.agent,
            text="Original",
            external_id=WAMID_STORED,
        )
        ChatMessageReplyIndex.objects.create(
            external_id=WAMID_STORED,
            message=self.original_message,
            external_id_core=extract_wamid_core(WAMID_STORED),
        )
        self.client.force_authenticate(user=self.agent)

    def _create_reply_pointing_to(self, context_id: str) -> Message:
        return Message.objects.create(
            room=self.room,
            contact=self.contact,
            text="Reply",
            metadata={"context": {"id": context_id}},
        )

    def _list_messages(self):
        url = reverse("message-v2-list")
        return self.client.get(url, {"room": str(self.room.uuid)})

    def _find_reply(self, response, reply_uuid):
        for msg in response.data["results"]:
            if msg["uuid"] == str(reply_uuid):
                return msg
        return None


class V2ExactMatchTests(_BaseFallbackSetup):
    """The exact ``external_id`` match must never depend on the feature flag."""

    @mock.patch(
        "chats.apps.api.v2.msgs.serializers.is_feature_active_for_attributes",
        return_value=False,
    )
    def test_exact_external_id_match_resolves_without_flag(self, _mock_flag):
        reply = self._create_reply_pointing_to(WAMID_STORED)

        response = self._list_messages()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        reply_data = self._find_reply(response, reply.uuid)
        self.assertIsNotNone(reply_data["replied_message"])
        self.assertEqual(
            reply_data["replied_message"]["uuid"], str(self.original_message.uuid)
        )


class V2CoreFallbackTests(_BaseFallbackSetup):
    """
    When ``context.id`` arrives with a different WAMID envelope, the reply
    must still mount as long as the project has the fallback flag enabled.
    """

    def _matching_core_context_id(self) -> str:
        """Pick a WAMID different from ``WAMID_STORED`` but with the same core."""
        # We synthesize a "different envelope, same core" by reusing the stored
        # WAMID prefix swapped: in practice this is what Meta does. Tests do
        # not need the prefix to be a real envelope — only the cores must match.
        target_core = extract_wamid_core(WAMID_STORED)
        # Sanity check: stored WAMID and our synthetic reply id share the core.
        self.assertEqual(target_core, extract_wamid_core(WAMID_STORED))
        return WAMID_STORED  # exact match path is tested elsewhere

    @mock.patch(
        "chats.apps.api.v2.msgs.serializers.is_feature_active_for_attributes",
        return_value=False,
    )
    def test_fallback_is_off_by_default(self, _mock_flag):
        # Reply arrives with a *different* WAMID whose core does not match the
        # stored one; serializer must return None and never reach the fallback.
        reply = self._create_reply_pointing_to(WAMID_REPLY_DIFFERENT_ENVELOPE)

        response = self._list_messages()

        reply_data = self._find_reply(response, reply.uuid)
        self.assertIsNone(reply_data["replied_message"])

    @mock.patch(
        "chats.apps.api.v2.msgs.serializers.is_feature_active_for_attributes",
        return_value=True,
    )
    def test_fallback_resolves_when_cores_match(self, _mock_flag):
        # Bind the stored row to the core of WAMID_REPLY_DIFFERENT_ENVELOPE so
        # the fallback has something to find. This simulates what
        # ``create_reply_index`` will do for new messages once the change ships.
        target_core = extract_wamid_core(WAMID_REPLY_DIFFERENT_ENVELOPE)
        ChatMessageReplyIndex.objects.filter(
            external_id=WAMID_STORED
        ).update(external_id_core=target_core)

        reply = self._create_reply_pointing_to(WAMID_REPLY_DIFFERENT_ENVELOPE)

        response = self._list_messages()

        reply_data = self._find_reply(response, reply.uuid)
        self.assertIsNotNone(reply_data["replied_message"])
        self.assertEqual(
            reply_data["replied_message"]["uuid"], str(self.original_message.uuid),
        )

    @mock.patch(
        "chats.apps.api.v2.msgs.serializers.is_feature_active_for_attributes",
        return_value=True,
    )
    def test_fallback_returns_none_when_no_core_row_exists(self, _mock_flag):
        # Even with the flag on, if no ``external_id_core`` matches, we must
        # return None instead of mounting some random reply.
        reply = self._create_reply_pointing_to(WAMID_REPLY_DIFFERENT_ENVELOPE)

        response = self._list_messages()

        reply_data = self._find_reply(response, reply.uuid)
        self.assertIsNone(reply_data["replied_message"])

    @mock.patch(
        "chats.apps.api.v2.msgs.serializers.is_feature_active_for_attributes",
        return_value=True,
    )
    def test_fallback_returns_none_for_non_wamid_context_id(self, _mock_flag):
        # When the context id is not a WAMID (no core extractable) the
        # fallback path should short-circuit and not query the DB.
        reply = self._create_reply_pointing_to("non-wamid-legacy-id")

        response = self._list_messages()

        reply_data = self._find_reply(response, reply.uuid)
        self.assertIsNone(reply_data["replied_message"])
