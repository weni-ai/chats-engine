import uuid
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase
from unittest.mock import MagicMock

from chats.apps.csat.models import CSATFlowProjectConfig
from chats.apps.csat.services import CSATFlowService
from chats.core.tests.mock import MockCacheClient
from chats.apps.projects.models.models import Project
from chats.apps.queues.models import Queue
from chats.apps.sectors.models import Sector
from chats.apps.rooms.models import Room


class MockFlowRESTClient:
    def start_flow(self, project, data):
        return MagicMock()


class MockJWTTokenGenerator:
    def generate_token(self, payload):
        return MagicMock()


class TestCSATFlowService(TestCase):
    def setUp(self):
        self.service = CSATFlowService(
            flows_client=MockFlowRESTClient(),
            cache_client=MockCacheClient(),
            token_generator=MockJWTTokenGenerator(),
        )
        self.project = Project.objects.create(name="Test Project")

    def _create_room(self) -> Room:
        sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=1,
            work_start="09:00",
            work_end="18:00",
        )
        queue = Queue.objects.create(name="Test Queue", sector=sector)

        return Room.objects.create(queue=queue)

    def test_get_flow_uuid_when_project_has_no_csat_flow_config(self):
        with self.assertRaises(ValueError) as context:
            self.service.get_flow_uuid(self.project.uuid)

        self.assertEqual(str(context.exception), "CSAT flow not found")

    @patch("chats.apps.csat.tests.test_services.MockCacheClient.get")
    @patch("chats.apps.csat.tests.test_services.MockCacheClient.set")
    def test_get_flow_uuid_when_project_has_csat_flow_config(self, mock_set, mock_get):
        mock_get.return_value = None
        mock_set.return_value = True
        csat_flow_project_config = CSATFlowProjectConfig.objects.create(
            project=self.project,
            flow_uuid=uuid.uuid4(),
            version=1,
        )
        self.assertEqual(
            self.service.get_flow_uuid(self.project.uuid),
            csat_flow_project_config.flow_uuid,
        )

        self.service.cache_client.get.assert_called_once_with(
            f"csat_flow_uuid:{str(self.project.uuid)}",
        )
        self.service.cache_client.set.assert_called_once_with(
            f"csat_flow_uuid:{str(self.project.uuid)}",
            str(csat_flow_project_config.flow_uuid),
            300,
        )

    @patch("chats.apps.csat.tests.test_services.MockCacheClient.get")
    @patch("chats.apps.csat.tests.test_services.MockCacheClient.set")
    @patch("chats.apps.csat.tests.test_services.CSATFlowProjectConfig.objects.filter")
    def test_get_flow_uuid_from_cache(self, mock_filter, mock_set, mock_get):
        flow_uuid = uuid.uuid4()
        mock_get.return_value = str(flow_uuid)
        mock_set.return_value = True
        mock_filter.return_value = None
        self.assertEqual(
            self.service.get_flow_uuid(self.project.uuid),
            flow_uuid,
        )
        self.service.cache_client.get.assert_called_once_with(
            f"csat_flow_uuid:{str(self.project.uuid)}",
        )
        self.service.cache_client.set.assert_not_called()
        mock_filter.assert_not_called()

    @patch("chats.apps.csat.tests.test_services.CSATFlowService.get_flow_uuid")
    def test_start_csat_flow_when_room_is_active(self, mock_get_flow_uuid):
        mock_get_flow_uuid.return_value = uuid.uuid4()
        room = self._create_room()

        with self.assertRaises(ValidationError) as context:
            self.service.start_csat_flow(room)

        self.assertEqual(context.exception.message, "Room is active")

    @patch("chats.apps.csat.tests.test_services.CSATFlowService.get_flow_uuid")
    @patch("chats.apps.csat.tests.test_services.MockJWTTokenGenerator.generate_token")
    @patch("chats.apps.csat.tests.test_services.MockFlowRESTClient.start_flow")
    def test_start_csat_flow(
        self, mock_start_flow, mock_generate_token, mock_get_flow_uuid
    ):
        mock_get_flow_uuid.return_value = uuid.uuid4()
        mock_generate_token.return_value = "test_token"
        mock_start_flow.return_value = {}
        room = self._create_room()

        room.is_active = False
        room.save(update_fields=["is_active"])

        self.service.start_csat_flow(room)
        self.service.flows_client.start_flow.assert_called_once_with(
            room.project,
            {
                "flow": str(mock_get_flow_uuid.return_value),
                "urns": [room.urn],
                "params": {
                    "room": str(room.uuid),
                    "token": mock_generate_token.return_value,
                },
            },
        )
