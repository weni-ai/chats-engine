import pendulum
import uuid
from unittest.mock import patch
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from chats.apps.projects.models.models import Project
from chats.apps.sectors.models import Sector
from chats.apps.queues.models import Queue
from chats.apps.api.v1.external.rooms.serializers import RoomFlowSerializer


class TestRoomFlowSerializerWeekendValidation(TestCase):
    def setUp(self):
        self.project = Project.objects.create(
            name="Test Project",
            timezone="America/Sao_Paulo"
        )
        
        # Criar setor com configuração de horários de trabalho
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="17:00",
            config={
                "working_hours": {
                    "open_in_weekends": True,
                    "schedules": {
                        "weekdays": {"start": "09:00", "end": "17:00"},
                        "saturday": {"start": "09:00", "end": "15:00"},
                        "sunday": {"start": None, "end": None}
                    }
                }
            }
        )
        
        # Criar queue para o setor
        self.queue = Queue.objects.create(
            name="Test Queue",
            sector=self.sector
        )

    def test_weekend_validation_saturday_within_hours(self):
        """Testa criação de sala no sábado dentro do horário permitido"""
        # Sábado às 10:00 (dentro do horário 09:00-15:00)
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
                "groups": [{"uuid": "group-uuid-1", "name": "VIP Customers"}]
            },
            "created_on": saturday_10am.isoformat(),
            "custom_fields": {"country": "brazil", "mood": "happy", "priority": "high"},
            "callback_url": "http://foo.bar/webhook",
            "flow_uuid": "flow-uuid-12345",
            "is_anon": False,
            "project_info": {"uuid": str(self.project.uuid), "name": "My Project"},
            "protocol": "1234567890"
        }
        
        serializer = RoomFlowSerializer(data=data)
        # Não deve levantar exceção pois está dentro do horário permitido
        self.assertTrue(serializer.is_valid())

    def test_weekend_validation_saturday_outside_hours(self):
        """Testa criação de sala no sábado fora do horário permitido"""
        # Sábado às 16:00 (fora do horário 09:00-15:00)
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
                "groups": [{"uuid": "group-uuid-1", "name": "VIP Customers"}]
            },
            "created_on": saturday_4pm.isoformat(),
            "custom_fields": {"country": "brazil", "mood": "happy", "priority": "high"},
            "callback_url": "http://foo.bar/webhook",
            "flow_uuid": "flow-uuid-12345",
            "is_anon": False,
            "project_info": {"uuid": str(self.project.uuid), "name": "My Project"},
            "protocol": "1234567890"
        }
        
        serializer = RoomFlowSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("detail", serializer.errors)
        self.assertIn("Contact cannot be done outside working hours", str(serializer.errors))

    def test_weekend_validation_sunday_closed(self):
        """Testa criação de sala no domingo quando o setor não atende"""
        # Domingo às 10:00 (setor não atende no domingo)
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
                "groups": [{"uuid": "group-uuid-1", "name": "VIP Customers"}]
            },
            "created_on": sunday_10am.isoformat(),
            "custom_fields": {"country": "brazil", "mood": "happy", "priority": "high"},
            "callback_url": "http://foo.bar/webhook",
            "flow_uuid": "flow-uuid-12345",
            "is_anon": False,
            "project_info": {"uuid": str(self.project.uuid), "name": "My Project"},
            "protocol": "1234567890"
        }
        
        serializer = RoomFlowSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("detail", serializer.errors)
        self.assertIn("Contact cannot be done outside working hours", str(serializer.errors))

    def test_weekend_validation_sector_not_open_weekends(self):
        """Testa criação de sala no fim de semana quando o setor não atende"""
        # Criar setor que não atende no fim de semana
        sector_no_weekend = Sector.objects.create(
            name="No Weekend Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="17:00",
            config={
                "working_hours": {
                    "open_in_weekends": False,
                    "schedules": {
                        "weekdays": {"start": "09:00", "end": "17:00"}
                    }
                }
            }
        )
        
        # Criar queue para o setor
        Queue.objects.create(
            name="No Weekend Queue",
            sector=sector_no_weekend
        )
        
        # Sábado às 10:00
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
                "groups": [{"uuid": "group-uuid-1", "name": "VIP Customers"}]
            },
            "created_on": saturday_10am.isoformat(),
            "custom_fields": {"country": "brazil", "mood": "happy", "priority": "high"},
            "callback_url": "http://foo.bar/webhook",
            "flow_uuid": "flow-uuid-12345",
            "is_anon": False,
            "project_info": {"uuid": str(self.project.uuid), "name": "My Project"},
            "protocol": "1234567890"
        }
        
        serializer = RoomFlowSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("detail", serializer.errors)
        self.assertIn("Contact cannot be done outside working hours", str(serializer.errors))

    def test_weekend_validation_sector_open_all_weekend(self):
        """Testa criação de sala no fim de semana quando o setor atende 24h"""
        # Criar setor que atende 24h no fim de semana
        sector_24h_weekend = Sector.objects.create(
            name="24h Weekend Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="17:00",
            config={
                "working_hours": {
                    "open_in_weekends": True,
                    "schedules": {
                        "weekdays": {"start": "09:00", "end": "17:00"},
                        "saturday": {"start": "00:00", "end": "23:59"},
                        "sunday": {"start": "00:00", "end": "23:59"}
                    }
                }
            }
        )
        
        # Criar queue para o setor
        Queue.objects.create(
            name="24h Weekend Queue",
            sector=sector_24h_weekend
        )
        
        # Domingo às 23:00
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
                "groups": [{"uuid": "group-uuid-1", "name": "VIP Customers"}]
            },
            "created_on": sunday_11pm.isoformat(),
            "custom_fields": {"country": "brazil", "mood": "happy", "priority": "high"},
            "callback_url": "http://foo.bar/webhook",
            "flow_uuid": "flow-uuid-12345",
            "is_anon": False,
            "project_info": {"uuid": str(self.project.uuid), "name": "My Project"},
            "protocol": "1234567890"
        }
        
        serializer = RoomFlowSerializer(data=data)
        # Deve ser válido pois o setor atende 24h no fim de semana
        self.assertTrue(serializer.is_valid())

    def test_weekend_validation_weekday_normal_hours(self):
        """Testa criação de sala em dia útil (não deve ser afetada pela validação de fim de semana)"""
        # Segunda-feira às 10:00
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
                "groups": [{"uuid": "group-uuid-1", "name": "VIP Customers"}]
            },
            "created_on": monday_10am.isoformat(),
            "custom_fields": {"country": "brazil", "mood": "happy", "priority": "high"},
            "callback_url": "http://foo.bar/webhook",
            "flow_uuid": "flow-uuid-12345",
            "is_anon": False,
            "project_info": {"uuid": str(self.project.uuid), "name": "My Project"},
            "protocol": "1234567890"
        }
        
        serializer = RoomFlowSerializer(data=data)
        # Deve ser válido pois é dia útil (a validação de fim de semana não se aplica)
        self.assertTrue(serializer.is_valid())

    def test_weekend_validation_sector_without_working_hours_config(self):
        """Testa criação de sala quando o setor não tem configuração de horários"""
        # Criar setor sem configuração de horários
        sector_no_config = Sector.objects.create(
            name="No Config Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="17:00",
            config={}  # Sem configuração de working_hours
        )
        
        # Criar queue para o setor
        Queue.objects.create(
            name="No Config Queue",
            sector=sector_no_config
        )
        
        # Sábado às 10:00
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
                "groups": [{"uuid": "group-uuid-1", "name": "VIP Customers"}]
            },
            "created_on": saturday_10am.isoformat(),
            "custom_fields": {"country": "brazil", "mood": "happy", "priority": "high"},
            "callback_url": "http://foo.bar/webhook",
            "flow_uuid": "flow-uuid-12345",
            "is_anon": False,
            "project_info": {"uuid": str(self.project.uuid), "name": "My Project"},
            "protocol": "1234567890"
        }
        
        serializer = RoomFlowSerializer(data=data)
        # Deve ser válido pois não há configuração de fim de semana (não valida nada)
        self.assertTrue(serializer.is_valid())

    def test_weekend_validation_edge_case_saturday_start_time(self):
        """Testa criação de sala no sábado exatamente no horário de início"""
        # Sábado às 09:00 (exatamente no horário de início)
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
                "groups": [{"uuid": "group-uuid-1", "name": "VIP Customers"}]
            },
            "created_on": saturday_9am.isoformat(),
            "custom_fields": {"country": "brazil", "mood": "happy", "priority": "high"},
            "callback_url": "http://foo.bar/webhook",
            "flow_uuid": "flow-uuid-12345",
            "is_anon": False,
            "project_info": {"uuid": str(self.project.uuid), "name": "My Project"},
            "protocol": "1234567890"
        }
        
        serializer = RoomFlowSerializer(data=data)
        # Deve ser válido pois está exatamente no horário de início
        self.assertTrue(serializer.is_valid())

    def test_weekend_validation_edge_case_saturday_end_time(self):
        """Testa criação de sala no sábado exatamente no horário de fim"""
        # Sábado às 15:00 (exatamente no horário de fim)
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
                "groups": [{"uuid": "group-uuid-1", "name": "VIP Customers"}]
            },
            "created_on": saturday_3pm.isoformat(),
            "custom_fields": {"country": "brazil", "mood": "happy", "priority": "high"},
            "callback_url": "http://foo.bar/webhook",
            "flow_uuid": "flow-uuid-12345",
            "is_anon": False,
            "project_info": {"uuid": str(self.project.uuid), "name": "My Project"},
            "protocol": "1234567890"
        }
        
        serializer = RoomFlowSerializer(data=data)
        # Deve ser válido pois está exatamente no horário de fim
        self.assertTrue(serializer.is_valid()) 