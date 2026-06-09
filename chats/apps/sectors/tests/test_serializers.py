from django.test import TestCase

from chats.apps.api.v1.sectors.serializers import (
    SectorInactivityTimeoutSerializer,
    SectorSerializer,
    SectorUpdateSerializer,
)
from chats.apps.projects.models import Project
from chats.apps.sectors.constants import (
    DEFAULT_CLOSE_ROOM_TIMEOUT_TIME,
    DEFAULT_MESSAGE_TIMEOUT_TIME,
    get_default_inactivity_timeout,
)
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


class TestSectorInactivityTimeoutSerializer(TestCase):
    """
    Validates the cross-field rules for the nested `inactivity_timeout` payload.
    """

    @staticmethod
    def _full_payload(**overrides):
        payload = {
            "is_message_timeout_enabled": True,
            "message_timeout_text": "warn",
            "message_timeout_time": 600,
            "is_close_room_enabled": True,
            "close_room_message_text": "bye",
            "close_room_timeout_time": 60,
        }
        payload.update(overrides)
        return payload

    def test_valid_full_payload_passes(self):
        serializer = SectorInactivityTimeoutSerializer(data=self._full_payload())
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_close_enabled_without_message_enabled_fails(self):
        payload = self._full_payload(is_message_timeout_enabled=False)
        serializer = SectorInactivityTimeoutSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn("is_close_room_enabled", serializer.errors)

    def test_message_enabled_without_message_timeout_time_fails(self):
        payload = self._full_payload(
            is_close_room_enabled=False,
            message_timeout_time=None,
        )
        serializer = SectorInactivityTimeoutSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn("message_timeout_time", serializer.errors)

    def test_close_enabled_without_close_timeout_time_fails(self):
        payload = self._full_payload(close_room_timeout_time=None)
        serializer = SectorInactivityTimeoutSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn("close_room_timeout_time", serializer.errors)

    def test_message_timeout_time_zero_is_rejected(self):
        payload = self._full_payload(message_timeout_time=0)
        serializer = SectorInactivityTimeoutSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn("message_timeout_time", serializer.errors)

    def test_disabled_features_accept_null_times(self):
        payload = self._full_payload(
            is_message_timeout_enabled=False,
            is_close_room_enabled=False,
            message_timeout_time=None,
            close_room_timeout_time=None,
        )
        serializer = SectorInactivityTimeoutSerializer(data=payload)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_blank_message_texts_are_accepted(self):
        payload = self._full_payload(
            message_timeout_text="",
            close_room_message_text="",
        )
        serializer = SectorInactivityTimeoutSerializer(data=payload)
        self.assertTrue(serializer.is_valid(), serializer.errors)


class TestSectorSerializerInactivityTimeout(TestCase):
    """
    Covers reading and writing `inactivity_timeout` through the public CRUD
    serializers.
    """

    def setUp(self):
        self.project = Project.objects.create(
            name="Test Project", timezone="America/Sao_Paulo"
        )
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=5,
            work_start="08:00",
            work_end="18:00",
        )

    def test_returns_defaults_when_field_is_none(self):
        self.assertIsNone(self.sector.inactivity_timeout)

        data = SectorSerializer(self.sector).data

        self.assertEqual(data["inactivity_timeout"], get_default_inactivity_timeout())
        self.assertEqual(
            data["inactivity_timeout"]["message_timeout_time"],
            DEFAULT_MESSAGE_TIMEOUT_TIME,
        )
        self.assertEqual(
            data["inactivity_timeout"]["close_room_timeout_time"],
            DEFAULT_CLOSE_ROOM_TIMEOUT_TIME,
        )
        self.assertFalse(data["inactivity_timeout"]["is_message_timeout_enabled"])
        self.assertFalse(data["inactivity_timeout"]["is_close_room_enabled"])

    def test_returns_stored_value_when_configured(self):
        stored = {
            "is_message_timeout_enabled": True,
            "message_timeout_text": "warn",
            "message_timeout_time": 900,
            "is_close_room_enabled": True,
            "close_room_message_text": "bye",
            "close_room_timeout_time": 120,
        }
        self.sector.inactivity_timeout = stored
        self.sector.save()

        data = SectorSerializer(self.sector).data
        self.assertEqual(data["inactivity_timeout"], stored)

    def test_update_writes_inactivity_timeout(self):
        payload = {
            "inactivity_timeout": {
                "is_message_timeout_enabled": True,
                "message_timeout_text": "warn",
                "message_timeout_time": 1200,
                "is_close_room_enabled": False,
                "close_room_message_text": "",
                "close_room_timeout_time": None,
            }
        }
        serializer = SectorUpdateSerializer(
            instance=self.sector, data=payload, partial=True
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()

        self.sector.refresh_from_db()
        self.assertEqual(
            self.sector.inactivity_timeout, payload["inactivity_timeout"]
        )

    def test_update_with_invalid_payload_raises(self):
        payload = {
            "inactivity_timeout": {
                "is_message_timeout_enabled": False,
                "message_timeout_text": "warn",
                "message_timeout_time": 600,
                "is_close_room_enabled": True,
                "close_room_message_text": "bye",
                "close_room_timeout_time": 60,
            }
        }
        serializer = SectorUpdateSerializer(
            instance=self.sector, data=payload, partial=True
        )
        self.assertFalse(serializer.is_valid())

    def test_update_with_null_clears_field_and_returns_defaults(self):
        self.sector.inactivity_timeout = {
            "is_message_timeout_enabled": True,
            "message_timeout_text": "warn",
            "message_timeout_time": 600,
            "is_close_room_enabled": False,
            "close_room_message_text": "",
            "close_room_timeout_time": None,
        }
        self.sector.save()

        serializer = SectorUpdateSerializer(
            instance=self.sector, data={"inactivity_timeout": None}, partial=True
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()

        self.sector.refresh_from_db()
        self.assertIsNone(self.sector.inactivity_timeout)

        data = SectorSerializer(self.sector).data
        self.assertEqual(data["inactivity_timeout"], get_default_inactivity_timeout())

    def test_update_without_inactivity_timeout_does_not_touch_field(self):
        previous_value = {
            "is_message_timeout_enabled": True,
            "message_timeout_text": "warn",
            "message_timeout_time": 600,
            "is_close_room_enabled": False,
            "close_room_message_text": "",
            "close_room_timeout_time": None,
        }
        self.sector.inactivity_timeout = previous_value
        self.sector.save()

        serializer = SectorUpdateSerializer(
            instance=self.sector, data={"name": "Renamed"}, partial=True
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()

        self.sector.refresh_from_db()
        self.assertEqual(self.sector.inactivity_timeout, previous_value)
        self.assertEqual(self.sector.name, "Renamed")
