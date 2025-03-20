from datetime import datetime, timedelta
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate
from django.utils import timezone
import pytz
from rest_framework.request import Request
from rest_framework.parsers import JSONParser

from chats.apps.accounts.models import User
from chats.apps.projects.models import Project, CustomStatusType, CustomStatus, ProjectPermission
from chats.apps.api.v1.projects.viewsets import CustomStatusViewSet


class TestCustomStatusViewSet(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        
        self.user = User.objects.create(
            email="test@test.com",
            first_name="Test",
            last_name="User",
            is_active=True
        )
        
        self.project = Project.objects.create(
            name="Test Project",
            timezone=pytz.timezone("America/Sao_Paulo")
        )
        
        self.project_permission = ProjectPermission.objects.create(
            user=self.user,
            project=self.project,
            status="ONLINE"
        )
        
        self.status_type = CustomStatusType.objects.create(
            name="Lunch",
            project=self.project
        )
        
        self.custom_status = CustomStatus.objects.create(
            user=self.user,
            status_type=self.status_type,
            is_active=True,
            break_time=0
        )
        
        self.viewset = CustomStatusViewSet()

    def test_last_status_with_active_status(self):
        """Testa o retorno do último status ativo do usuário"""
        request = self.factory.get('/custom-status/last-status/')
        force_authenticate(request, user=self.user)
        request = Request(request)
        request.user = self.user
        
        response = self.viewset.last_status(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['uuid'], str(self.custom_status.uuid))
        self.assertTrue(response.data['is_active'])

    def test_last_status_without_active_status(self):
        """Testa o retorno quando não há status ativo"""

        CustomStatus.objects.all().update(is_active=False)
        
        request = self.factory.get('/custom-status/last-status/')
        force_authenticate(request, user=self.user)
        request = Request(request)
        request.user = self.user
        
        response = self.viewset.last_status(request)
        
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data['detail'], 'No status found')

    def test_close_status_success(self):
        """Testa o fechamento bem-sucedido de um status"""
        end_time = timezone.now() + timedelta(hours=1)
        
        request = self.factory.post(
            f'/custom-status/{self.custom_status.pk}/close-status/',
            {
                'end_time': end_time.isoformat(),
                'is_active': True
            },
            format='json'
        )
        force_authenticate(request, user=self.user)
        request = Request(request, parsers=[JSONParser()])
        request.user = self.user
        
        response = self.viewset.close_status(request, pk=self.custom_status.pk)
        
        self.assertEqual(response.status_code, 200)
        self.custom_status.refresh_from_db()
        self.assertFalse(self.custom_status.is_active)
        self.assertTrue(self.custom_status.break_time > 0)

    def test_close_status_not_last_active(self):
        """Testa tentativa de fechar um status que não é o último ativo"""

        newer_status = CustomStatus.objects.create(
            user=self.user,
            status_type=self.status_type,
            is_active=True,
            break_time=0
        )
        
        end_time = timezone.now() + timedelta(hours=1)
        request = self.factory.post(
            f'/custom-status/{self.custom_status.pk}/close-status/',
            {'end_time': end_time.isoformat()},
            format='json'
        )
        force_authenticate(request, user=self.user)
        request = Request(request, parsers=[JSONParser()])
        request.user = self.user
        
        response = self.viewset.close_status(request, pk=self.custom_status.pk)
        
        self.assertEqual(response.status_code, 400)
        self.assertIn("not the last active status", response.data['detail'])

    def test_close_status_missing_end_time(self):
        """Testa tentativa de fechar um status sem fornecer end_time"""
        request = self.factory.post(
            f'/custom-status/{self.custom_status.pk}/close-status/',
            {},
            format='json'
        )
        force_authenticate(request, user=self.user)
        request = Request(request, parsers=[JSONParser()])
        request.user = self.user
        
        response = self.viewset.close_status(request, pk=self.custom_status.pk)
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['detail'], 'end_time is required.')

    def test_close_status_invalid_end_time(self):
        """Testa tentativa de fechar um status com end_time em formato inválido"""
        request = self.factory.post(
            f'/custom-status/{self.custom_status.pk}/close-status/',
            {'end_time': 'invalid-date-format'},
            format='json'
        )
        force_authenticate(request, user=self.user)
        request = Request(request, parsers=[JSONParser()])
        request.user = self.user
        
        response = self.viewset.close_status(request, pk=self.custom_status.pk)
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('Invalid end_time format', response.data['detail'])