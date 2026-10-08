from datetime import timedelta
from unittest.mock import patch

from django.db import transaction
from django.test import TestCase
from django.utils import timezone

from chats.apps.api.utils import create_user_and_token
from chats.apps.contacts.models import Contact
from chats.apps.msgs.models import Message
from chats.apps.projects.models.models import (
    ContactGroupFlowReference,
    FlowStart,
    Project,
    ProjectPermission,
)
from chats.apps.projects.usecases.exceptions import (
    ActiveFlowStartError,
    NoContactsToStartFlowError,
    StartFlowPermissionError,
)
from chats.apps.projects.usecases.start_flow import (
    StartFlowUseCase,
    StartOutOffWhatsappFlowUseCase,
)
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector

DEFAULT_ROOMS_LIMIT = 5
WHATSAPP_WINDOW_EXPIRED_DAYS = 2

MOCK_FLOW_START_RESPONSE = {
    "uuid": "ext-flow-start-uuid",
    "flow": {"name": "Test Flow", "uuid": "flow-uuid-001"},
}


@patch("chats.apps.projects.usecases.start_flow.create_room_feedback_message")
@patch("chats.apps.projects.usecases.start_flow.FlowRESTClient")
@patch.object(Room, "notify_room")
@patch.object(Room, "request_callback")
class StartFlowUseCaseTests(TestCase):
    def setUp(self):
        self.user, _ = create_user_and_token("flowusecase")
        self.project = Project.objects.create(name="Flow Project")
        self.permission = ProjectPermission.objects.create(
            project=self.project,
            user=self.user,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=DEFAULT_ROOMS_LIMIT,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Queue", sector=self.sector)
        self.contact = Contact.objects.create(name="Maria", external_id="ext-maria")

    def _mock_client(self, mock_client_cls):
        mock_instance = mock_client_cls.return_value
        mock_instance.start_flow.return_value = (200, MOCK_FLOW_START_RESPONSE)
        return mock_instance

    def _room(self, days_old=WHATSAPP_WINDOW_EXPIRED_DAYS, is_active=True):
        room = Room.objects.create(
            queue=self.queue,
            contact=self.contact,
            user=self.user,
            urn="whatsapp:5500000000001",
            is_active=is_active,
        )
        Room.objects.filter(pk=room.pk).update(
            created_on=timezone.now() - timedelta(days=days_old)
        )
        room.refresh_from_db()
        return room

    def _data(self, room=None):
        data = {
            "flow": "flow-uuid-001",
            "contacts": [self.contact.external_id],
            "contact_name": "Maria",
        }
        if room is not None:
            data["room"] = str(room.pk)
        return data

    def test_without_permission_does_not_call_flows(
        self, _callback, _notify, mock_client_cls, _feedback
    ):
        mock_instance = self._mock_client(mock_client_cls)
        outsider, _ = create_user_and_token("outsiderflow")

        with self.assertRaises(StartFlowPermissionError):
            StartFlowUseCase().execute(self.project, outsider, self._data())

        mock_instance.start_flow.assert_not_called()
        self.assertEqual(FlowStart.objects.count(), 0)

    def test_active_flow_start_does_not_mark_the_room_waiting(
        self, _callback, _notify, mock_client_cls, _feedback
    ):
        self._mock_client(mock_client_cls)
        room = self._room()
        FlowStart.objects.create(
            project=self.project,
            permission=self.permission,
            room=room,
            is_deleted=False,
        )

        with self.assertRaises(ActiveFlowStartError):
            StartFlowUseCase().execute(self.project, self.user, self._data(room))

        room.refresh_from_db()
        self.assertFalse(room.is_waiting)

    def test_invalid_room_id_is_logged_and_flow_still_starts(
        self, _callback, _notify, mock_client_cls, _feedback
    ):
        mock_instance = self._mock_client(mock_client_cls)
        data = self._data()
        data["room"] = "not-a-uuid"

        with patch("chats.apps.projects.usecases.start_flow.logger") as mock_logger:
            result = StartFlowUseCase().execute(self.project, self.user, data)

        self.assertEqual(result["uuid"], "ext-flow-start-uuid")
        mock_logger.warning.assert_called_once()
        mock_instance.start_flow.assert_called_once()
        sent = mock_instance.start_flow.call_args[0][1]
        self.assertNotIn("contact_name", sent)
        self.assertNotIn("email", sent)

    def test_expired_room_is_linked_and_marked_waiting(
        self, mock_callback, mock_notify, mock_client_cls, mock_feedback
    ):
        self._mock_client(mock_client_cls)
        room = self._room()

        StartFlowUseCase().execute(self.project, self.user, self._data(room))

        room.refresh_from_db()
        self.assertTrue(room.is_waiting)
        mock_callback.assert_called_once()
        mock_feedback.assert_called_once()
        mock_notify.assert_called_once()
        flow_start = FlowStart.objects.get(project=self.project, room=room)
        self.assertEqual(flow_start.contact_data["external_id"], "ext-maria")
        self.assertNotIn("email", flow_start.contact_data)

    def test_open_window_does_not_link_the_room(
        self, _callback, _notify, mock_client_cls, mock_feedback
    ):
        self._mock_client(mock_client_cls)
        room = self._room(days_old=0)
        Message.objects.create(room=room, contact=self.contact, text="oi")

        StartFlowUseCase().execute(self.project, self.user, self._data(room))

        flow_start = FlowStart.objects.get(project=self.project)
        self.assertIsNone(flow_start.room)
        mock_feedback.assert_not_called()

    def test_flows_failure_rolls_back_the_waiting_room(
        self, _callback, _notify, mock_client_cls, _feedback
    ):
        mock_instance = self._mock_client(mock_client_cls)
        mock_instance.start_flow.side_effect = RuntimeError("flows down")
        room = self._room()

        with self.assertRaises(RuntimeError):
            StartFlowUseCase().execute(self.project, self.user, self._data(room))

        room.refresh_from_db()
        self.assertFalse(room.is_waiting)
        self.assertEqual(FlowStart.objects.count(), 0)


@patch("chats.apps.projects.usecases.start_flow.FlowRESTClient")
class StartOutOffWhatsappFlowUseCaseTests(TestCase):
    def setUp(self):
        self.user, _ = create_user_and_token("dispatchusecase")
        self.project = Project.objects.create(name="Dispatch Project")
        ProjectPermission.objects.create(
            project=self.project,
            user=self.user,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        self.sector = Sector.objects.create(
            name="Sector",
            project=self.project,
            rooms_limit=DEFAULT_ROOMS_LIMIT,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Queue", sector=self.sector)

    def _mock_client(self, mock_client_cls):
        mock_instance = mock_client_cls.return_value
        mock_instance.start_flow.return_value = (200, MOCK_FLOW_START_RESPONSE)
        return mock_instance

    def _expired_contact(self, name, external_id, user=None):
        with transaction.atomic():
            contact = Contact.objects.create(name=name, external_id=external_id)
            room = Room.objects.create(
                queue=self.queue,
                contact=contact,
                user=user or self.user,
                urn="whatsapp:5500000000001",
                is_active=True,
            )
            Room.objects.filter(pk=room.pk).update(
                created_on=timezone.now() - timedelta(days=WHATSAPP_WINDOW_EXPIRED_DAYS)
            )
        return contact

    def test_empty_contact_list_does_not_call_flows(self, mock_client_cls):
        mock_instance = self._mock_client(mock_client_cls)

        with self.assertRaises(NoContactsToStartFlowError):
            StartFlowUseCase().execute_for_contacts(
                self.project, self.user, "flow-uuid-001", []
            )

        mock_instance.start_flow.assert_not_called()

    def test_dispatch_skips_ignored_and_in_window_contacts(self, mock_client_cls):
        mock_instance = self._mock_client(mock_client_cls)
        self._expired_contact("Ana", "ext-ana")
        self._expired_contact("Bruno", "ext-bruno")
        inside = Contact.objects.create(name="Inside", external_id="ext-inside")
        room = Room.objects.create(
            queue=self.queue,
            contact=inside,
            user=self.user,
            urn="whatsapp:5500000000009",
            is_active=True,
        )
        Message.objects.create(room=room, contact=inside, text="oi")

        StartOutOffWhatsappFlowUseCase().execute(
            project=self.project,
            user=self.user,
            flow="flow-uuid-001",
            ignored_contacts=["ext-ana"],
            filters={"user_email": self.user.email},
        )

        sent = mock_instance.start_flow.call_args[0][1]
        self.assertEqual(set(sent.keys()), {"flow", "contacts"})
        self.assertEqual(sent["contacts"], ["ext-bruno"])
        flow_start = FlowStart.objects.get(project=self.project)
        self.assertEqual(flow_start.contact_data, {"external_ids": ["ext-bruno"]})
        self.assertNotIn("email", flow_start.contact_data)
        refs = ContactGroupFlowReference.objects.filter(flow_start=flow_start)
        self.assertEqual(
            list(refs.values_list("external_id", flat=True)), ["ext-bruno"]
        )

    def test_included_contacts_are_the_only_recipients(self, mock_client_cls):
        mock_instance = self._mock_client(mock_client_cls)
        self._expired_contact("Ana", "ext-ana")
        self._expired_contact("Ana Dois", "ext-ana-2")
        self._expired_contact("Bruno", "ext-bruno")

        StartOutOffWhatsappFlowUseCase().execute(
            project=self.project,
            user=self.user,
            flow="flow-uuid-001",
            ignored_contacts=["ext-bruno"],
            filters={},
            send_to_all=False,
            included_contacts=["ext-ana", "ext-ana-2", "ext-missing"],
        )

        sent = mock_instance.start_flow.call_args[0][1]
        self.assertEqual(sent["contacts"], ["ext-ana", "ext-ana-2"])

    def test_flows_failure_rolls_back_the_bulk_flow_start(self, mock_client_cls):
        mock_instance = self._mock_client(mock_client_cls)
        mock_instance.start_flow.side_effect = RuntimeError("flows down")
        self._expired_contact("Ana", "ext-ana")

        with self.assertRaises(RuntimeError):
            StartFlowUseCase().execute_for_contacts(
                self.project, self.user, "flow-uuid-001", ["ext-ana"]
            )

        self.assertEqual(FlowStart.objects.count(), 0)
        self.assertEqual(ContactGroupFlowReference.objects.count(), 0)
