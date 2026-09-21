from unittest.mock import patch

from django.test import TestCase

from chats.apps.api.v1.dto.queue_dto import QueueDTO
from chats.apps.api.v1.dto.sector_dto import SectorDTO
from chats.apps.feature_version.models import IntegratedFeature
from chats.apps.projects.models import Project
from chats.apps.projects.usecases.sector_creation import SectorCreationUseCase
from chats.apps.queues.models import Queue
from chats.apps.sectors.models import Sector, SectorTag


class TestCreateSectorDTO(TestCase):
    def test_returns_dtos_from_message_body(self):
        body = {
            "sectors": [
                {
                    "name": "Sector A",
                    "working_hours": {"init": "09:00", "close": "18:00"},
                    "service_limit": 4,
                    "tags": ["tag1", "tag2"],
                    "queues": [{"name": "Queue A1"}, {"name": "Queue A2"}],
                },
                {
                    "name": "Sector B",
                    "working_hours": {"init": "10:00", "close": "16:00"},
                    "service_limit": 2,
                    "tags": [],
                    "queues": [{"name": "Queue B1"}],
                },
            ]
        }

        dtos = SectorCreationUseCase.create_sector_dto(body)

        self.assertEqual(len(dtos), 2)
        self.assertIsInstance(dtos[0], SectorDTO)
        self.assertEqual(dtos[0].name, "Sector A")
        self.assertEqual(dtos[0].service_limit, 4)
        self.assertEqual(dtos[0].tags, ["tag1", "tag2"])
        self.assertEqual([q.name for q in dtos[0].queues], ["Queue A1", "Queue A2"])
        self.assertEqual(dtos[1].name, "Sector B")
        self.assertEqual(len(dtos[1].queues), 1)
        self.assertIsInstance(dtos[1].queues[0], QueueDTO)


class TestIntegrateFeature(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="SC Test Project")
        self.user_email = "agent@test.com"

    def _make_dto(self, name, queue_names):
        return SectorDTO(
            working_hours={"init": "09:00", "close": "18:00"},
            service_limit=5,
            tags=["tag-a"],
            name=name,
            queues=[QueueDTO(name=qn) for qn in queue_names],
        )

    def _body(self):
        return {
            "project_uuid": str(self.project.uuid),
            "user_email": self.user_email,
        }

    @patch(
        "chats.apps.projects.usecases.sector_creation.FlowsEDAClient.request_ticketer"
    )
    def test_integrate_feature_creates_sector_tags_queues_and_calls_eda(
        self, mock_request_ticketer
    ):
        dtos = [self._make_dto("New Sector", ["Q1", "Q2"])]
        use_case = SectorCreationUseCase()

        use_case.integrate_feature(self._body(), dtos)

        sector = Sector.objects.get(name="New Sector", project=self.project)
        self.assertEqual(sector.rooms_limit, 5)
        self.assertTrue(Queue.objects.filter(sector=sector, name="Q1").exists())
        self.assertTrue(Queue.objects.filter(sector=sector, name="Q2").exists())
        self.assertTrue(SectorTag.objects.filter(sector=sector, name="tag-a").exists())

        # DTO uuids should be populated for later steps
        self.assertEqual(dtos[0].uuid, str(sector.uuid))
        for queue_dto in dtos[0].queues:
            self.assertTrue(
                Queue.objects.filter(uuid=queue_dto.uuid, sector=sector).exists()
            )

        mock_request_ticketer.assert_called_once()
        call_kwargs = mock_request_ticketer.call_args.kwargs
        content = call_kwargs["content"]
        self.assertEqual(content["name"], "New Sector")
        self.assertEqual(content["user_email"], self.user_email)
        self.assertEqual(len(content["queues"]), 2)

    @patch(
        "chats.apps.projects.usecases.sector_creation.FlowsEDAClient.request_ticketer"
    )
    def test_integrate_feature_is_idempotent(self, mock_request_ticketer):
        existing = Sector.objects.create(
            name="Existing Sector",
            project=self.project,
            rooms_limit=10,
            work_start="08:00",
            work_end="20:00",
        )
        Queue.objects.create(name="Q1", sector=existing)
        SectorTag.objects.create(name="tag-a", sector=existing)

        dtos = [self._make_dto("Existing Sector", ["Q1", "Q2"])]
        use_case = SectorCreationUseCase()
        use_case.integrate_feature(self._body(), dtos)

        # Original sector kept with its original rooms_limit (get_or_create defaults are ignored on get)
        existing.refresh_from_db()
        self.assertEqual(existing.rooms_limit, 10)

        # Only one duplicate tag/queue created
        self.assertEqual(
            SectorTag.objects.filter(sector=existing, name="tag-a").count(), 1
        )
        self.assertEqual(Queue.objects.filter(sector=existing).count(), 2)
        mock_request_ticketer.assert_called_once()


class TestCreateIntegratedFeatureObject(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="IF Test Project")

    def test_create_integrated_feature_object_persists_with_dto_dicts(self):
        dto = SectorDTO(
            working_hours={"init": "09:00", "close": "18:00"},
            service_limit=5,
            tags=["t"],
            name="Sector",
            queues=[QueueDTO(name="Q1")],
        )
        # Mimic state after integrate_feature ran: queues need a uuid attr
        dto.queues[0].uuid = "queue-uuid"

        use_case = SectorCreationUseCase()
        body = {
            "project_uuid": str(self.project.uuid),
            "feature_uuid": "feat-123",
        }

        use_case.create_integrated_feature_object(body, [dto])

        feature = IntegratedFeature.objects.get(project=self.project)
        self.assertEqual(feature.feature, "feat-123")
        self.assertEqual(len(feature.current_version), 1)
        self.assertEqual(feature.current_version[0]["name"], "Sector")
        self.assertEqual(feature.current_version[0]["queues"][0]["name"], "Q1")
        self.assertEqual(feature.current_version[0]["queues"][0]["uuid"], "queue-uuid")
