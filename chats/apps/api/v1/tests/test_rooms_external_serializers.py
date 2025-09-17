import pendulum
from django.test import TestCase
from rest_framework.exceptions import ValidationError

from chats.apps.api.v1.external.rooms.serializers import RoomFlowSerializer
from chats.apps.projects.models.models import Project
from chats.apps.queues.models import Queue
from chats.apps.sectors.models import Sector


class TestRoomFlowSerializerWeekendValidation(TestCase):
    def setUp(self):
        self.project = Project.objects.create(
            name="Test Project", timezone="America/Sao_Paulo"
        )

        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="17:00",
            working_day={
                "working_hours": {
                    "open_in_weekends": True,
                    "schedules": {
                        "monday": [{"start": "09:00", "end": "17:00"}],
                        "tuesday": [{"start": "09:00", "end": "17:00"}],
                        "wednesday": [{"start": "09:00", "end": "17:00"}],
                        "thursday": [{"start": "09:00", "end": "17:00"}],
                        "friday": [{"start": "09:00", "end": "17:00"}],
                        "saturday": [{"start": "09:00", "end": "15:00"}],
                        "sunday": None,
                    },
                }
            },
        )

        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)

    def test_weekend_validation_saturday_within_hours(self):
        """Test room creation on Saturday within allowed hours"""
        saturday_10am = pendulum.datetime(2023, 8, 26, 10, 0, 0, tz="America/Sao_Paulo")

        data = {
            "sector_uuid": str(self.sector.uuid),
            "contact": {
                "external_id": "095be615-a8ad-4c33-8e9c-c7612fbf6c9f",
                "name": "Foo Bar",
                "email": "foobar@email.com",
                "phone": "+250788123123",
                "urn": "tel:+250788123123",
                "custom_fields": {"age": 30, "preferences": "chat"},
                "groups": [{"uuid": "group-uuid-1", "name": "VIP Customers"}],
            },
            "created_on": saturday_10am.isoformat(),
            "custom_fields": {"country": "brazil", "mood": "happy", "priority": "high"},
            "callback_url": "http://foo.bar/webhook",
            "flow_uuid": "flow-uuid-12345",
            "is_anon": False,
            "project_info": {"uuid": str(self.project.uuid), "name": "My Project"},
            "protocol": "1234567890",
        }

        serializer = RoomFlowSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_weekend_validation_saturday_outside_hours(self):
        """Test room creation on Saturday outside allowed hours"""
        saturday_4pm = pendulum.datetime(2023, 8, 26, 16, 0, 0, tz="America/Sao_Paulo")

        data = {
            "sector_uuid": str(self.sector.uuid),
            "contact": {
                "external_id": "095be615-a8ad-4c33-8e9c-c7612fbf6c9f",
                "name": "Foo Bar",
                "email": "foobar@email.com",
                "phone": "+250788123123",
                "urn": "tel:+250788123123",
                "custom_fields": {"age": 30, "preferences": "chat"},
                "groups": [{"uuid": "group-uuid-1", "name": "VIP Customers"}],
            },
            "created_on": saturday_4pm.isoformat(),
            "custom_fields": {"country": "brazil", "mood": "happy", "priority": "high"},
            "callback_url": "http://foo.bar/webhook",
            "flow_uuid": "flow-uuid-12345",
            "is_anon": False,
            "project_info": {"uuid": str(self.project.uuid), "name": "My Project"},
            "protocol": "1234567890",
        }

        serializer = RoomFlowSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        with self.assertRaises(ValidationError) as cm:
            serializer.save()
        self.assertIn("Contact cannot be done outside working hours", str(cm.exception))

    def test_weekend_validation_sunday_closed(self):
        """Test room creation on Sunday when sector is closed"""
        sunday_10am = pendulum.datetime(2023, 8, 27, 10, 0, 0, tz="America/Sao_Paulo")

        data = {
            "sector_uuid": str(self.sector.uuid),
            "contact": {
                "external_id": "095be615-a8ad-4c33-8e9c-c7612fbf6c9f",
                "name": "Foo Bar",
                "email": "foobar@email.com",
                "phone": "+250788123123",
                "urn": "tel:+250788123123",
                "custom_fields": {"age": 30, "preferences": "chat"},
                "groups": [{"uuid": "group-uuid-1", "name": "VIP Customers"}],
            },
            "created_on": sunday_10am.isoformat(),
            "custom_fields": {"country": "brazil", "mood": "happy", "priority": "high"},
            "callback_url": "http://foo.bar/webhook",
            "flow_uuid": "flow-uuid-12345",
            "is_anon": False,
            "project_info": {"uuid": str(self.project.uuid), "name": "My Project"},
            "protocol": "1234567890",
        }

        serializer = RoomFlowSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        with self.assertRaises(ValidationError) as cm:
            serializer.save()
        self.assertIn("Contact cannot be done outside working hours", str(cm.exception))

    def test_weekend_validation_sector_not_open_weekends(self):
        """Test room creation on weekend when sector doesn't operate"""
        sector_no_weekend = Sector.objects.create(
            name="No Weekend Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="17:00",
            working_day={
                "working_hours": {
                    "open_in_weekends": False,
                    "schedules": {
                        "monday": [{"start": "09:00", "end": "17:00"}],
                        "tuesday": [{"start": "09:00", "end": "17:00"}],
                        "wednesday": [{"start": "09:00", "end": "17:00"}],
                        "thursday": [{"start": "09:00", "end": "17:00"}],
                        "friday": [{"start": "09:00", "end": "17:00"}],
                        "saturday": None,
                        "sunday": None,
                    },
                }
            },
        )

        Queue.objects.create(name="No Weekend Queue", sector=sector_no_weekend)

        saturday_10am = pendulum.datetime(2023, 8, 26, 10, 0, 0, tz="America/Sao_Paulo")

        data = {
            "sector_uuid": str(sector_no_weekend.uuid),
            "contact": {
                "external_id": "095be615-a8ad-4c33-8e9c-c7612fbf6c9f",
                "name": "Foo Bar",
                "email": "foobar@email.com",
                "phone": "+250788123123",
                "urn": "tel:+250788123123",
                "custom_fields": {"age": 30, "preferences": "chat"},
                "groups": [{"uuid": "group-uuid-1", "name": "VIP Customers"}],
            },
            "created_on": saturday_10am.isoformat(),
            "custom_fields": {"country": "brazil", "mood": "happy", "priority": "high"},
            "callback_url": "http://foo.bar/webhook",
            "flow_uuid": "flow-uuid-12345",
            "is_anon": False,
            "project_info": {"uuid": str(self.project.uuid), "name": "My Project"},
            "protocol": "1234567890",
        }

        serializer = RoomFlowSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        with self.assertRaises(ValidationError) as cm:
            serializer.save()
        self.assertIn("Contact cannot be done outside working hours", str(cm.exception))

    def test_weekend_validation_sector_open_all_weekend(self):
        """Test room creation on weekend when sector operates 24h"""
        sector_24h_weekend = Sector.objects.create(
            name="24h Weekend Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="17:00",
            working_day={
                "working_hours": {
                    "open_in_weekends": True,
                    "schedules": {
                        "monday": [{"start": "09:00", "end": "17:00"}],
                        "tuesday": [{"start": "09:00", "end": "17:00"}],
                        "wednesday": [{"start": "09:00", "end": "17:00"}],
                        "thursday": [{"start": "09:00", "end": "17:00"}],
                        "friday": [{"start": "09:00", "end": "17:00"}],
                        "saturday": [{"start": "00:00", "end": "23:59"}],
                        "sunday": [{"start": "00:00", "end": "23:59"}],
                    },
                }
            },
        )

        Queue.objects.create(name="24h Weekend Queue", sector=sector_24h_weekend)

        sunday_11pm = pendulum.datetime(2023, 8, 27, 23, 0, 0, tz="America/Sao_Paulo")

        data = {
            "sector_uuid": str(sector_24h_weekend.uuid),
            "contact": {
                "external_id": "095be615-a8ad-4c33-8e9c-c7612fbf6c9f",
                "name": "Foo Bar",
                "email": "foobar@email.com",
                "phone": "+250788123123",
                "urn": "tel:+250788123123",
                "custom_fields": {"age": 30, "preferences": "chat"},
                "groups": [{"uuid": "group-uuid-1", "name": "VIP Customers"}],
            },
            "created_on": sunday_11pm.isoformat(),
            "custom_fields": {"country": "brazil", "mood": "happy", "priority": "high"},
            "callback_url": "http://foo.bar/webhook",
            "flow_uuid": "flow-uuid-12345",
            "is_anon": False,
            "project_info": {"uuid": str(self.project.uuid), "name": "My Project"},
            "protocol": "1234567890",
        }

        serializer = RoomFlowSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_weekend_validation_weekday_normal_hours(self):
        """Test room creation on weekday (should not be affected by weekend validation)"""
        monday_10am = pendulum.datetime(2023, 8, 28, 10, 0, 0, tz="America/Sao_Paulo")

        data = {
            "sector_uuid": str(self.sector.uuid),
            "contact": {
                "external_id": "095be615-a8ad-4c33-8e9c-c7612fbf6c9f",
                "name": "Foo Bar",
                "email": "foobar@email.com",
                "phone": "+250788123123",
                "urn": "tel:+250788123123",
                "custom_fields": {"age": 30, "preferences": "chat"},
                "groups": [{"uuid": "group-uuid-1", "name": "VIP Customers"}],
            },
            "created_on": monday_10am.isoformat(),
            "custom_fields": {"country": "brazil", "mood": "happy", "priority": "high"},
            "callback_url": "http://foo.bar/webhook",
            "flow_uuid": "flow-uuid-12345",
            "is_anon": False,
            "project_info": {"uuid": str(self.project.uuid), "name": "My Project"},
            "protocol": "1234567890",
        }

        serializer = RoomFlowSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_weekend_validation_sector_without_working_hours_config(self):
        """Test room creation when sector has no working hours configuration"""
        sector_no_config = Sector.objects.create(
            name="No Config Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="17:00",
            working_day={},
        )

        Queue.objects.create(name="No Config Queue", sector=sector_no_config)

        saturday_10am = pendulum.datetime(2023, 8, 26, 10, 0, 0, tz="America/Sao_Paulo")

        data = {
            "sector_uuid": str(sector_no_config.uuid),
            "contact": {
                "external_id": "095be615-a8ad-4c33-8e9c-c7612fbf6c9f",
                "name": "Foo Bar",
                "email": "foobar@email.com",
                "phone": "+250788123123",
                "urn": "tel:+250788123123",
                "custom_fields": {"age": 30, "preferences": "chat"},
                "groups": [{"uuid": "group-uuid-1", "name": "VIP Customers"}],
            },
            "created_on": saturday_10am.isoformat(),
            "custom_fields": {"country": "brazil", "mood": "happy", "priority": "high"},
            "callback_url": "http://foo.bar/webhook",
            "flow_uuid": "flow-uuid-12345",
            "is_anon": False,
            "project_info": {"uuid": str(self.project.uuid), "name": "My Project"},
            "protocol": "1234567890",
        }

        serializer = RoomFlowSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_weekend_validation_edge_case_saturday_start_time(self):
        """Test room creation on Saturday exactly at start time"""
        saturday_9am = pendulum.datetime(2023, 8, 26, 9, 0, 0, tz="America/Sao_Paulo")

        data = {
            "sector_uuid": str(self.sector.uuid),
            "contact": {
                "external_id": "095be615-a8ad-4c33-8e9c-c7612fbf6c9f",
                "name": "Foo Bar",
                "email": "foobar@email.com",
                "phone": "+250788123123",
                "urn": "tel:+250788123123",
                "custom_fields": {"age": 30, "preferences": "chat"},
                "groups": [{"uuid": "group-uuid-1", "name": "VIP Customers"}],
            },
            "created_on": saturday_9am.isoformat(),
            "custom_fields": {"country": "brazil", "mood": "happy", "priority": "high"},
            "callback_url": "http://foo.bar/webhook",
            "flow_uuid": "flow-uuid-12345",
            "is_anon": False,
            "project_info": {"uuid": str(self.project.uuid), "name": "My Project"},
            "protocol": "1234567890",
        }

        serializer = RoomFlowSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_weekend_validation_edge_case_saturday_end_time(self):
        """Test room creation on Saturday exactly at end time"""
        saturday_3pm = pendulum.datetime(2023, 8, 26, 15, 0, 0, tz="America/Sao_Paulo")

        data = {
            "sector_uuid": str(self.sector.uuid),
            "contact": {
                "external_id": "095be615-a8ad-4c33-8e9c-c7612fbf6c9f",
                "name": "Foo Bar",
                "email": "foobar@email.com",
                "phone": "+250788123123",
                "urn": "tel:+250788123123",
                "custom_fields": {"age": 30, "preferences": "chat"},
                "groups": [{"uuid": "group-uuid-1", "name": "VIP Customers"}],
            },
            "created_on": saturday_3pm.isoformat(),
            "custom_fields": {"country": "brazil", "mood": "happy", "priority": "high"},
            "callback_url": "http://foo.bar/webhook",
            "flow_uuid": "flow-uuid-12345",
            "is_anon": False,
            "project_info": {"uuid": str(self.project.uuid), "name": "My Project"},
            "protocol": "1234567890",
        }

        serializer = RoomFlowSerializer(data=data)
        self.assertTrue(serializer.is_valid())
