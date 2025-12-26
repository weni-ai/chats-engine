from datetime import time
from unittest.mock import MagicMock, patch

from django.test import TestCase
from rest_framework import serializers

from chats.apps.accounts.models import User
from chats.apps.api.v1.sectors.serializers import SectorSerializer
from chats.apps.projects.models import Project
from chats.apps.sectors.models import Sector


class SectorSerializerValidateTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project", timezone="UTC")
        self.user = User.objects.create_user(
            email="admin@test.com", first_name="Admin", last_name="Test"
        )
        self.request = MagicMock()
        self.request.user = self.user

    def test_validate_work_end_greater_than_work_start(self):
        serializer = SectorSerializer(context={"request": self.request})

        data = {
            "name": "Test Sector",
            "project": self.project,
            "rooms_limit": 10,
            "work_start": time(9, 0),
            "work_end": time(17, 0),
        }

        result = serializer.validate(data)

        self.assertEqual(result["work_start"], time(9, 0))
        self.assertEqual(result["work_end"], time(17, 0))

    def test_validate_work_end_not_greater_than_work_start_raises_error(self):
        serializer = SectorSerializer(context={"request": self.request})

        data = {
            "name": "Test Sector",
            "project": self.project,
            "rooms_limit": 10,
            "work_start": time(17, 0),
            "work_end": time(9, 0),
        }

        with self.assertRaises(serializers.ValidationError) as context:
            serializer.validate(data)

        self.assertIn("work_end", str(context.exception).lower())

    def test_validate_work_end_equal_to_work_start_raises_error(self):
        serializer = SectorSerializer(context={"request": self.request})

        data = {
            "name": "Test Sector",
            "project": self.project,
            "rooms_limit": 10,
            "work_start": time(9, 0),
            "work_end": time(9, 0),
        }

        with self.assertRaises(serializers.ValidationError) as context:
            serializer.validate(data)

        self.assertIn("work_end", str(context.exception).lower())

    def test_validate_without_work_times_passes(self):
        serializer = SectorSerializer(context={"request": self.request})

        data = {
            "name": "Test Sector",
            "project": self.project,
            "rooms_limit": 10,
        }

        result = serializer.validate(data)

        self.assertIsNotNone(result)

    def test_validate_with_only_work_start_passes(self):
        serializer = SectorSerializer(context={"request": self.request})

        data = {
            "name": "Test Sector",
            "project": self.project,
            "rooms_limit": 10,
            "work_start": time(9, 0),
        }

        result = serializer.validate(data)

        self.assertIsNotNone(result)

    def test_validate_with_only_work_end_passes(self):
        serializer = SectorSerializer(context={"request": self.request})

        data = {
            "name": "Test Sector",
            "project": self.project,
            "rooms_limit": 10,
            "work_end": time(17, 0),
        }

        result = serializer.validate(data)

        self.assertIsNotNone(result)

    @patch("chats.apps.api.v1.sectors.serializers.is_feature_active")
    def test_validate_automatic_message_feature_flag_off_raises_error(
        self, mock_feature
    ):
        mock_feature.return_value = False

        serializer = SectorSerializer(context={"request": self.request})

        data = {
            "name": "Test Sector",
            "project": self.project,
            "rooms_limit": 10,
            "automatic_message": {"is_active": True, "text": "Hello!"},
        }

        with self.assertRaises(serializers.ValidationError) as context:
            serializer.validate(data)

        self.assertIn(
            "automatic_message_feature_flag_is_not_active",
            str(context.exception),
        )

    @patch("chats.apps.api.v1.sectors.serializers.is_feature_active")
    def test_validate_automatic_message_feature_flag_on_passes(self, mock_feature):
        mock_feature.return_value = True

        serializer = SectorSerializer(context={"request": self.request})

        data = {
            "name": "Test Sector",
            "project": self.project,
            "rooms_limit": 10,
            "automatic_message": {"is_active": True, "text": "Hello!"},
        }

        result = serializer.validate(data)

        self.assertTrue(result["is_automatic_message_active"])
        self.assertEqual(result["automatic_message_text"], "Hello!")
        self.assertNotIn("automatic_message", result)

    @patch("chats.apps.api.v1.sectors.serializers.is_feature_active")
    def test_validate_automatic_message_inactive_feature_flag_off_passes(
        self, mock_feature
    ):
        mock_feature.return_value = False

        serializer = SectorSerializer(context={"request": self.request})

        data = {
            "name": "Test Sector",
            "project": self.project,
            "rooms_limit": 10,
            "automatic_message": {"is_active": False, "text": "Hello!"},
        }

        result = serializer.validate(data)

        self.assertFalse(result["is_automatic_message_active"])

    @patch("chats.apps.api.v1.sectors.serializers.validate_is_csat_enabled")
    def test_validate_csat_enabled_calls_validator(self, mock_validator):
        sector = Sector.objects.create(
            name="Existing Sector", project=self.project, rooms_limit=10
        )

        serializer = SectorSerializer(
            instance=sector, context={"request": self.request}
        )

        data = {"is_csat_enabled": True}

        serializer.validate(data)

        mock_validator.assert_called_once()

    def test_validate_secondary_project_string(self):
        serializer = SectorSerializer(context={"request": self.request})

        data = {
            "name": "Test Sector",
            "project": self.project,
            "rooms_limit": 10,
            "config": {"secondary_project": "some-uuid-string"},
        }

        result = serializer.validate(data)

        self.assertEqual(result["secondary_project"], {"uuid": "some-uuid-string"})

    def test_validate_secondary_project_dict(self):
        serializer = SectorSerializer(context={"request": self.request})

        data = {
            "name": "Test Sector",
            "project": self.project,
            "rooms_limit": 10,
            "config": {"secondary_project": {"uuid": "some-uuid", "name": "Secondary"}},
        }

        result = serializer.validate(data)

        self.assertEqual(
            result["secondary_project"], {"uuid": "some-uuid", "name": "Secondary"}
        )

    def test_validate_uses_instance_work_times_when_not_in_data(self):
        sector = Sector.objects.create(
            name="Existing Sector",
            project=self.project,
            rooms_limit=10,
            work_start=time(9, 0),
            work_end=time(17, 0),
        )

        serializer = SectorSerializer(
            instance=sector, context={"request": self.request}
        )

        data = {"name": "Updated Sector"}

        result = serializer.validate(data)

        self.assertIsNotNone(result)

    def test_validate_update_work_end_only_checks_against_instance_start(self):
        sector = Sector.objects.create(
            name="Existing Sector",
            project=self.project,
            rooms_limit=10,
            work_start=time(9, 0),
            work_end=time(17, 0),
        )

        serializer = SectorSerializer(
            instance=sector, context={"request": self.request}
        )

        data = {"work_end": time(8, 0)}

        with self.assertRaises(serializers.ValidationError):
            serializer.validate(data)

    def test_validate_update_work_start_only_checks_against_instance_end(self):
        sector = Sector.objects.create(
            name="Existing Sector",
            project=self.project,
            rooms_limit=10,
            work_start=time(9, 0),
            work_end=time(17, 0),
        )

        serializer = SectorSerializer(
            instance=sector, context={"request": self.request}
        )

        data = {"work_start": time(18, 0)}

        with self.assertRaises(serializers.ValidationError):
            serializer.validate(data)
