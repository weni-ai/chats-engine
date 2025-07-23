from django.test import TestCase

from chats.apps.api.v1.sectors.serializers import SectorUpdateSerializer
from chats.apps.projects.models import Project
from chats.apps.sectors.models import Sector


class TestSectorUpdateSerializer(TestCase):
    def setUp(self):
        """Set up test data."""
        self.project = Project.objects.create(
            name="Test Project", timezone="America/Sao_Paulo"
        )

        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=5,
            work_start="08:00",
            work_end="18:00",
            config={
                "working_hours": {
                    "open_in_weekends": True,
                    "schedules": {
                        "saturday": {"start": "09:00", "end": "15:00"},
                        "sunday": {"start": "10:00", "end": "14:00"},
                    },
                },
                "existing_field": "should_be_preserved",
            },
        )

    def test_update_with_empty_config(self):
        """
        Test that sending an empty config dictionary doesn't modify the existing config.
        Empty dicts don't overwrite existing config.
        """
        serializer = SectorUpdateSerializer()

        data = {"config": {}}

        updated_sector = serializer.update(self.sector, data)

        updated_sector.refresh_from_db()

        self.assertEqual(updated_sector.config, self.sector.config)

        self.assertEqual(updated_sector.name, "Test Sector")
        self.assertEqual(updated_sector.rooms_limit, 5)

    def test_update_with_new_config_data(self):
        """
        Test that sending new config data updates only the specified fields
        while preserving existing config fields.
        """
        serializer = SectorUpdateSerializer()

        data = {
            "config": {
                "working_hours": {
                    "open_in_weekends": False,
                    "schedules": {"saturday": {"start": "10:00", "end": "16:00"}},
                },
                "new_field": "new_value",
            }
        }

        updated_sector = serializer.update(self.sector, data)

        updated_sector.refresh_from_db()

        expected_config = {
            "working_hours": {
                "open_in_weekends": False,
                "schedules": {"saturday": {"start": "10:00", "end": "16:00"}},
            },
            "existing_field": "should_be_preserved",
            "new_field": "new_value",
        }

        self.assertEqual(updated_sector.config, expected_config)

        self.assertEqual(updated_sector.name, "Test Sector")
        self.assertEqual(updated_sector.rooms_limit, 5)

    def test_update_without_config_field(self):
        """
        Test that not sending the config field doesn't modify the existing config.
        """
        serializer = SectorUpdateSerializer()

        data = {"name": "Updated Sector Name", "rooms_limit": 10}

        updated_sector = serializer.update(self.sector, data)

        updated_sector.refresh_from_db()

        self.assertEqual(updated_sector.config, self.sector.config)

        self.assertEqual(updated_sector.name, "Updated Sector Name")
        self.assertEqual(updated_sector.rooms_limit, 10)

    def test_update_with_none_config(self):
        """
        Test that sending config as None doesn't modify the existing config.
        """
        serializer = SectorUpdateSerializer()

        data = {"config": None}

        updated_sector = serializer.update(self.sector, data)

        updated_sector.refresh_from_db()

        self.assertEqual(updated_sector.config, self.sector.config)

        self.assertEqual(updated_sector.name, "Test Sector")
        self.assertEqual(updated_sector.rooms_limit, 5)

    def test_update_with_partial_config(self):
        """
        Test that sending partial config data updates the specified fields
        and overwrites nested objects (this is the current behavior).
        """
        serializer = SectorUpdateSerializer()

        data = {"config": {"working_hours": {"open_in_weekends": False}}}

        updated_sector = serializer.update(self.sector, data)

        updated_sector.refresh_from_db()

        self.assertEqual(
            updated_sector.config["working_hours"]["open_in_weekends"], False
        )
        self.assertEqual(updated_sector.config["existing_field"], "should_be_preserved")

        self.assertNotIn("schedules", updated_sector.config["working_hours"])

        self.assertEqual(
            updated_sector.config["working_hours"], {"open_in_weekends": False}
        )

    def test_update_with_explicit_empty_config(self):
        """
        Test that if we want to clear the config, we need to send it explicitly.
        This shows how to clear the config if needed.
        """
        serializer = SectorUpdateSerializer()

        data = {"config": {"working_hours": {}, "existing_field": None}}

        updated_sector = serializer.update(self.sector, data)

        updated_sector.refresh_from_db()

        self.assertEqual(updated_sector.config["working_hours"], {})
        self.assertIsNone(updated_sector.config["existing_field"])
