from datetime import timedelta
from unittest.mock import patch
from urllib.parse import urlencode

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.api.utils import create_user_and_token
from chats.apps.contacts.models import Contact
from chats.apps.msgs.models import Message
from chats.apps.projects.models.models import (
    ContactGroupFlowReference,
    FlowStart,
    Project,
    ProjectPermission,
)
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector

MOCK_FLOW_START_RESPONSE = {
    "uuid": "ext-flow-start-uuid",
    "flow": {"name": "Test Flow", "uuid": "flow-uuid-001"},
}
DEFAULT_ROOM_AGE_DAYS = 2


@patch("chats.apps.projects.usecases.start_flow.FlowRESTClient")
class OutOffWhatsappStartFlowTests(APITestCase):
    def setUp(self):
        self.user, self.token = create_user_and_token("dispatchagent")
        self.project = Project.objects.create(
            name="Dispatch Project", flows_authorization="fake-token"
        )
        self.permission = ProjectPermission.objects.create(
            project=self.project,
            user=self.user,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Queue", sector=self.sector)
        self.url = reverse(
            "project-out_off_whatsapp_response_window_start_flow",
            kwargs={"uuid": str(self.project.uuid)},
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        flag_patcher = patch(
            "chats.apps.api.v1.projects.viewsets.is_out_off_whatsapp_response_window_enabled",
            return_value=True,
        )
        self._feature_flag = flag_patcher.start()
        self.addCleanup(flag_patcher.stop)

    def _mock_client(self, mock_client_cls):
        mock_instance = mock_client_cls.return_value
        mock_instance.start_flow.return_value = MOCK_FLOW_START_RESPONSE
        return mock_instance

    def _contact(self, name, external_id):
        return Contact.objects.create(name=name, external_id=external_id)

    def _room(
        self, contact, urn, queue=None, days_old=DEFAULT_ROOM_AGE_DAYS, user=None
    ):
        room = Room.objects.create(
            queue=queue or self.queue,
            contact=contact,
            user=user or self.user,
            urn=urn,
            is_active=True,
        )
        Room.objects.filter(pk=room.pk).update(
            created_on=timezone.now() - timedelta(days=days_old)
        )
        room.refresh_from_db()
        return room

    def _post(self, payload=None, **params):
        url = self.url
        if params:
            url = f"{self.url}?{urlencode(params)}"
        return self.client.post(
            url, payload or {"flow": "flow-uuid-001"}, format="json"
        )

    def test_missing_flow_returns_400(self, mock_client_cls):
        self._mock_client(mock_client_cls)
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_feature_flag_off_does_not_call_flows(self, mock_client_cls):
        mock_instance = self._mock_client(mock_client_cls)
        self._feature_flag.return_value = False
        self._room(self._contact("Ana", "ext-ana"), "whatsapp:5500000000001")

        response = self._post()

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        mock_instance.start_flow.assert_not_called()
        self.assertEqual(FlowStart.objects.filter(project=self.project).count(), 0)

    def test_user_without_permission_returns_404(self, mock_client_cls):
        self._mock_client(mock_client_cls)
        _, token = create_user_and_token("nopermdispatch")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = self._post()
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_sends_everyone_outside_the_window_except_ignored(self, mock_client_cls):
        mock_instance = self._mock_client(mock_client_cls)
        self._room(self._contact("Ana", "ext-ana"), "whatsapp:5500000000001")
        self._room(self._contact("Bruno", "ext-bruno"), "whatsapp:5500000000002")
        inside = self._contact("Inside", "ext-inside")
        room = self._room(inside, "whatsapp:5500000000003", days_old=0)
        Message.objects.create(room=room, contact=inside, text="oi")
        Room.objects.filter(pk=room.pk).update(
            created_on=timezone.now() - timedelta(days=2)
        )

        response = self._post(
            {"flow": "flow-uuid-001", "ignored_contacts": ["ext-ana"]},
            limit=1,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        sent = mock_instance.start_flow.call_args[0][1]
        self.assertEqual(set(sent.keys()), {"flow", "contacts"})
        self.assertEqual(sent["flow"], "flow-uuid-001")
        self.assertEqual(sent["contacts"], ["ext-bruno"])

        flow_start = FlowStart.objects.get(project=self.project)
        self.assertEqual(flow_start.contact_data, {"external_ids": ["ext-bruno"]})
        self.assertNotIn("email", flow_start.contact_data)
        refs = ContactGroupFlowReference.objects.filter(flow_start=flow_start)
        self.assertEqual(
            list(refs.values_list("external_id", flat=True)), ["ext-bruno"]
        )

    def test_user_sector_and_search_narrow_the_dispatch(self, mock_client_cls):
        mock_instance = self._mock_client(mock_client_cls)
        other_user, _ = create_user_and_token("otherdispatch")
        other_sector = Sector.objects.create(
            name="Other",
            project=self.project,
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
        )
        other_queue = Queue.objects.create(name="Other queue", sector=other_sector)
        self._room(self._contact("Maria", "ext-maria"), "whatsapp:5500000000001")
        self._room(
            self._contact("Other agent", "ext-other"),
            "whatsapp:5500000000002",
            user=other_user,
        )
        self._room(
            self._contact("Other sector", "ext-sector"),
            "whatsapp:5500000000003",
            queue=other_queue,
        )

        response = self._post(
            user=self.user.email,
            sectors=str(self.sector.uuid),
            search="maria",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        sent = mock_instance.start_flow.call_args[0][1]["contacts"]
        self.assertEqual(sent, ["ext-maria"])

    def test_included_contacts_do_not_dispatch_the_rest(self, mock_client_cls):
        mock_instance = self._mock_client(mock_client_cls)
        self._room(self._contact("Ana", "ext-ana"), "whatsapp:5500000000001")
        self._room(self._contact("Ana Dois", "ext-ana-2"), "whatsapp:5500000000002")
        self._room(self._contact("Bruno", "ext-bruno"), "whatsapp:5500000000003")

        response = self._post(
            {
                "flow": "flow-uuid-001",
                "send_to_all": False,
                "included_contacts": ["ext-ana", "ext-ana-2"],
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        sent = mock_instance.start_flow.call_args[0][1]["contacts"]
        self.assertEqual(sent, ["ext-ana", "ext-ana-2"])

    def test_empty_included_contacts_does_not_call_flows(self, mock_client_cls):
        mock_instance = self._mock_client(mock_client_cls)
        self._room(self._contact("Ana", "ext-ana"), "whatsapp:5500000000001")

        response = self._post(
            {"flow": "flow-uuid-001", "send_to_all": False, "included_contacts": []}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_instance.start_flow.assert_not_called()

    def test_all_ignored_does_not_call_flows(self, mock_client_cls):
        mock_instance = self._mock_client(mock_client_cls)
        self._room(self._contact("Ana", "ext-ana"), "whatsapp:5500000000001")

        response = self._post(
            {"flow": "flow-uuid-001", "ignored_contacts": ["ext-ana"]}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_instance.start_flow.assert_not_called()
        self.assertEqual(FlowStart.objects.filter(project=self.project).count(), 0)

    def test_invalid_queue_returns_400(self, mock_client_cls):
        self._mock_client(mock_client_cls)
        response = self._post(queues="not-a-uuid")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
