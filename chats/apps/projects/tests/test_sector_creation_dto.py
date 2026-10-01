from django.test import SimpleTestCase

from chats.apps.projects.usecases.sector_creation import SectorCreationUseCase


class CreateSectorDtoTests(SimpleTestCase):
    def test_maps_payload_sectors_and_queues(self):
        body = {
            "sectors": [
                {
                    "name": "Support",
                    "service_limit": 5,
                    "working_hours": {"init": "08:00", "close": "18:00"},
                    "tags": ["vip"],
                    "queues": [{"name": "Default"}, {"name": "Priority"}],
                }
            ]
        }

        dtos = SectorCreationUseCase.create_sector_dto(body)

        self.assertEqual(len(dtos), 1)
        sector = dtos[0]
        self.assertEqual(sector.name, "Support")
        self.assertEqual(sector.service_limit, 5)
        self.assertEqual(sector.working_hours, {"init": "08:00", "close": "18:00"})
        self.assertEqual(sector.tags, ["vip"])
        self.assertEqual(
            [queue.name for queue in sector.queues], ["Default", "Priority"]
        )

    def test_returns_empty_list_when_there_are_no_sectors(self):
        self.assertEqual(SectorCreationUseCase.create_sector_dto({"sectors": []}), [])
