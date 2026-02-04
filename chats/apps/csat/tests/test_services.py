import uuid
from unittest.mock import Mock, patch

from django.conf import settings
from django.core.exceptions import ValidationError
from django.test import TestCase

from chats.apps.api.authentication.token import JWTTokenGenerator
from chats.apps.api.v1.internal.rest_clients.flows_rest_client import FlowRESTClient
from chats.apps.csat.flows.definitions.flow import (
    CSAT_FLOW_DEFINITION_DATA,
    CSAT_FLOW_VERSION,
)
from chats.apps.csat.models import CSATFlowProjectConfig
from chats.apps.csat.services import CSATFlowService
from chats.apps.projects.models.models import Project
from chats.apps.queues.models import Queue
from chats.apps.sectors.models import Sector
from chats.apps.rooms.models import Room
from chats.core.cache import CacheClient


class TestCSATFlowService(TestCase):
    def setUp(self):
        self.mock_cache_client = Mock(spec=CacheClient)
        self.mock_flows_client = Mock(spec=FlowRESTClient)
        self.mock_token_generator = Mock(spec=JWTTokenGenerator)

        self.service = CSATFlowService(
            flows_client=self.mock_flows_client,
            cache_client=self.mock_cache_client,
            token_generator=self.mock_token_generator,
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
        self.mock_cache_client.get.return_value = None

        with self.assertRaises(ValueError) as context:
            self.service.get_flow_uuid(self.project.uuid)

        self.assertEqual(str(context.exception), "CSAT flow not found")

    def test_get_flow_uuid_when_project_has_csat_flow_config(self):
        self.mock_cache_client.get.return_value = None
        self.mock_cache_client.set.return_value = True
        csat_flow_project_config = CSATFlowProjectConfig.objects.create(
            project=self.project,
            flow_uuid=uuid.uuid4(),
            version=1,
        )
        self.assertEqual(
            self.service.get_flow_uuid(self.project.uuid),
            csat_flow_project_config.flow_uuid,
        )

        self.mock_cache_client.get.assert_called_once_with(
            f"csat_flow_uuid:{str(self.project.uuid)}",
        )
        self.mock_cache_client.set.assert_called_once_with(
            f"csat_flow_uuid:{str(self.project.uuid)}",
            str(csat_flow_project_config.flow_uuid),
            300,
        )

    @patch("chats.apps.csat.tests.test_services.CSATFlowProjectConfig.objects.filter")
    def test_get_flow_uuid_from_cache(self, mock_filter):
        flow_uuid = uuid.uuid4()
        self.mock_cache_client.get.return_value = str(flow_uuid)
        self.mock_cache_client.set.return_value = True

        mock_query = Mock()
        mock_filter.return_value = mock_query
        mock_query.values_list.return_value.first.return_value = None

        self.assertEqual(
            self.service.get_flow_uuid(self.project.uuid),
            flow_uuid,
        )
        self.mock_cache_client.get.assert_called_once_with(
            f"csat_flow_uuid:{str(self.project.uuid)}",
        )
        self.mock_cache_client.set.assert_not_called()
        mock_filter.assert_not_called()

    def test_start_csat_flow_when_room_is_active(self):
        mock_flow_uuid = uuid.uuid4()
        self.service.get_flow_uuid = Mock(return_value=mock_flow_uuid)

        room = self._create_room()

        with self.assertRaises(ValidationError) as context:
            self.service.start_csat_flow(room)

        self.assertEqual(context.exception.message, "Room is active")

    def test_start_csat_flow(self):
        mock_flow_uuid = uuid.uuid4()
        self.service.get_flow_uuid = Mock(return_value=mock_flow_uuid)
        self.mock_token_generator.generate_token.return_value = "test_token"
        self.mock_flows_client.start_flow.return_value = {}

        room = self._create_room()

        room.is_active = False
        room.save(update_fields=["is_active"])

        self.service.start_csat_flow(room)
        self.mock_flows_client.start_flow.assert_called_once_with(
            room.project,
            {
                "flow": str(mock_flow_uuid),
                "urns": [room.urn],
                "params": {
                    "room": str(room.uuid),
                    "token": "test_token",
                    "webhook_url": f"{settings.CHATS_BASE_URL}/v1/internal/csat/",
                },
            },
        )

    def test_create_csat_flow(self):
        self.assertFalse(
            CSATFlowProjectConfig.objects.filter(project=self.project).exists()
        )
        flow_uuid = uuid.uuid4()
        self.mock_flows_client.create_or_update_flow.return_value = Mock(
            status_code=200,
            json=Mock(return_value={"results": [{"uuid": flow_uuid}]}),
        )
        self.service.create_csat_flow(self.project)
        self.mock_flows_client.create_or_update_flow.assert_called_once_with(
            self.project,
            CSAT_FLOW_DEFINITION_DATA,
        )

        config = CSATFlowProjectConfig.objects.filter(project=self.project).first()

        self.assertIsNotNone(config)

        self.assertEqual(
            config.flow_uuid,
            flow_uuid,
        )
        self.assertEqual(
            config.version,
            CSAT_FLOW_VERSION,
        )

    def test_create_csat_flow_when_config_already_exists(self):
        CSATFlowProjectConfig.objects.create(
            project=self.project,
            flow_uuid=uuid.uuid4(),
            version=CSAT_FLOW_VERSION - 1,
        )
        self.assertTrue(
            CSATFlowProjectConfig.objects.filter(project=self.project).exists()
        )
        flow_uuid = uuid.uuid4()
        self.mock_flows_client.create_or_update_flow.return_value = Mock(
            status_code=200,
            json=Mock(return_value={"results": [{"uuid": flow_uuid}]}),
        )
        self.service.create_csat_flow(self.project)
        self.mock_flows_client.create_or_update_flow.assert_called_once_with(
            self.project,
            CSAT_FLOW_DEFINITION_DATA,
        )

        config = CSATFlowProjectConfig.objects.filter(project=self.project).first()

        self.assertIsNotNone(config)
        self.assertEqual(config.flow_uuid, flow_uuid)
        self.assertEqual(config.version, CSAT_FLOW_VERSION)

    def test_cannot_create_csat_flow_when_flow_creation_fails(self):
        status_code = 500
        response_content = "Failed to create CSAT flow"
        self.mock_flows_client.create_or_update_flow.return_value = Mock(
            status_code=status_code,
            content=response_content,
            json=Mock(return_value={"detail": response_content}),
        )
        with self.assertRaises(Exception) as context:
            self.service.create_csat_flow(self.project)

        self.assertEqual(
            str(context.exception),
            f"Failed to create CSAT flow [{status_code}]: {response_content}",
        )
