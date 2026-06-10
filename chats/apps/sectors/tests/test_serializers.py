import uuid
from unittest.mock import patch

from django.conf import settings
from django.test import TestCase
from rest_framework import serializers

from chats.apps.api.v1.sectors.serializers import (
    SectorUpdateSerializer,
    validate_custom_csat_flow_uuid,
)
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


class TestValidateCustomCsatFlowUuid(TestCase):
    def setUp(self):
        self.project = Project.objects.create(
            name="Test Project", timezone="America/Sao_Paulo"
        )
        self.flow_uuid = uuid.uuid4()

    @patch("chats.apps.api.v1.sectors.serializers.is_feature_active_for_attributes")
    def test_allows_any_value_when_feature_flag_is_on(self, mock_flag):
        mock_flag.return_value = True
        result = validate_custom_csat_flow_uuid(self.project, self.flow_uuid)
        self.assertEqual(result, self.flow_uuid)

    @patch("chats.apps.api.v1.sectors.serializers.is_feature_active_for_attributes")
    def test_allows_none_when_feature_flag_is_on(self, mock_flag):
        mock_flag.return_value = True
        result = validate_custom_csat_flow_uuid(self.project, None)
        self.assertIsNone(result)

    @patch("chats.apps.api.v1.sectors.serializers.is_feature_active_for_attributes")
    def test_allows_clearing_existing_value_when_flag_is_off(self, mock_flag):
        mock_flag.return_value = False
        result = validate_custom_csat_flow_uuid(
            self.project, None, current_value=self.flow_uuid
        )
        self.assertIsNone(result)

    @patch("chats.apps.api.v1.sectors.serializers.is_feature_active_for_attributes")
    def test_raises_when_setting_value_and_flag_is_off(self, mock_flag):
        mock_flag.return_value = False
        with self.assertRaises(serializers.ValidationError) as ctx:
            validate_custom_csat_flow_uuid(self.project, self.flow_uuid)
        self.assertEqual(
            ctx.exception.detail["custom_csat_flow_uuid"][0].code,
            "custom_csat_flow_feature_flag_is_off",
        )

    @patch("chats.apps.api.v1.sectors.serializers.is_feature_active_for_attributes")
    def test_raises_when_changing_value_and_flag_is_off(self, mock_flag):
        mock_flag.return_value = False
        new_uuid = uuid.uuid4()
        with self.assertRaises(serializers.ValidationError) as ctx:
            validate_custom_csat_flow_uuid(
                self.project, new_uuid, current_value=self.flow_uuid
            )
        self.assertEqual(
            ctx.exception.detail["custom_csat_flow_uuid"][0].code,
            "custom_csat_flow_feature_flag_is_off",
        )

    @patch("chats.apps.api.v1.sectors.serializers.is_feature_active_for_attributes")
    def test_allows_none_when_no_current_value_and_flag_is_off(self, mock_flag):
        mock_flag.return_value = False
        result = validate_custom_csat_flow_uuid(self.project, None)
        self.assertIsNone(result)

    @patch("chats.apps.api.v1.sectors.serializers.is_feature_active_for_attributes")
    def test_passes_correct_attributes_to_feature_flag(self, mock_flag):
        mock_flag.return_value = True
        validate_custom_csat_flow_uuid(self.project, self.flow_uuid)
        mock_flag.assert_called_once_with(
            settings.CUSTOM_CSAT_FLOW_FEATURE_FLAG_KEY,
            {"projectUUID": str(self.project.uuid)},
        )
