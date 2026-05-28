from django.test import TestCase
from django.utils import timezone
from django.core.cache import cache
from unittest.mock import patch, MagicMock

from chats.apps.projects.usecases.status_service import InServiceStatusTracker
from chats.apps.projects.models.models import CustomStatusType, CustomStatus
from chats.apps.accounts.models import User
from chats.apps.projects.models import Project


class InServiceStatusTrackerTests(TestCase):
    def setUp(self):
        cache.clear()
        
        self.project = Project.objects.create(name="Test Project")
        
        self.user = User.objects.create(
            email="test@example.com",
            first_name="Test",
            last_name="User"
        )
        
        self.status_type = CustomStatusType.objects.create(
            name=InServiceStatusTracker.STATUS_NAME,
            project=self.project,
            is_deleted=False,
            config={"created_by_system": True}
        )

    def tearDown(self):
        cache.clear()

    def test_get_cache_timeout(self):
        """Testa se o método get_cache_timeout retorna o timeout correto"""
        original_projects = InServiceStatusTracker.DEFAULT_TIMEOUT_PROJECTS.copy()
        InServiceStatusTracker.DEFAULT_TIMEOUT_PROJECTS = [self.project.pk]
        
        try:
            self.assertEqual(
                InServiceStatusTracker.get_cache_timeout(self.project.pk),
                InServiceStatusTracker.DEFAULT_CACHE_TIMEOUT
            )
            
            self.assertEqual(
                InServiceStatusTracker.get_cache_timeout(999),
                InServiceStatusTracker.EXTENDED_CACHE_TIMEOUT
            )
        finally:
            InServiceStatusTracker.DEFAULT_TIMEOUT_PROJECTS = original_projects

    def test_get_cache_keys(self):
        """Testa se o método get_cache_keys retorna as chaves corretas"""
        user_id = 123
        project_uuid = "456"
        
        keys = InServiceStatusTracker.get_cache_keys(user_id, project_uuid)
        
        self.assertEqual(keys["room_count"], f"in_service_room_count:{user_id}:{project_uuid}")
        self.assertEqual(keys["status_id"], f"in_service_status_id:{user_id}:{project_uuid}")
        self.assertEqual(keys["start_time"], f"in_service_start_time:{user_id}:{project_uuid}")

    def test_get_or_create_status_type(self):
        """Testa se o método get_or_create_status_type obtém ou cria um status type"""
        status_type = InServiceStatusTracker.get_or_create_status_type(self.project)
        self.assertEqual(status_type.name, InServiceStatusTracker.STATUS_NAME)
        self.assertEqual(status_type.project, self.project)
        
        new_project = Project.objects.create(name="New Project")
        new_status_type = InServiceStatusTracker.get_or_create_status_type(new_project)
        
        self.assertEqual(new_status_type.name, InServiceStatusTracker.STATUS_NAME)
        self.assertEqual(new_status_type.project, new_project)
        self.assertEqual(new_status_type.config, {"created_by_system": True})

    @patch('chats.apps.projects.usecases.status_service.cache')
    def test_get_status_from_cache_success(self, mock_cache):
        """Testa se _get_status_from_cache retorna o status se ele existir no cache"""
        status = CustomStatus.objects.create(
            user=self.user,
            status_type=self.status_type,
            is_active=True,
            project=self.project,
            break_time=0
        )
        
        mock_cache.get.return_value = str(status.uuid)
        
        with patch('chats.apps.projects.usecases.status_service.CustomStatus.objects.get') as mock_get:
            mock_get.return_value = status
            result, from_cache = InServiceStatusTracker._get_status_from_cache(self.user.id, self.project.uuid)
            self.assertEqual(result, status)
            self.assertTrue(from_cache)
            mock_get.assert_called_once()

    @patch('chats.apps.projects.usecases.status_service.cache')
    def test_get_status_from_cache_not_found(self, mock_cache):
        """Testa se _get_status_from_cache retorna None quando o status não existir no cache"""
        mock_cache.get.return_value = None
        
        result, from_cache = InServiceStatusTracker._get_status_from_cache(self.user.id, self.project.uuid)
        
        self.assertIsNone(result)
        self.assertFalse(from_cache)

    def test_get_status_from_db(self):
        """Testa se _get_status_from_db retorna o status do banco de dados"""
        status = CustomStatus.objects.create(
            user=self.user,
            status_type=self.status_type,
            is_active=True,
            project=self.project,
            break_time=0
        )
        
        result = InServiceStatusTracker._get_status_from_db(self.user, self.project)
        
        self.assertEqual(result, status)
        
        status.is_active = False
        status.save()
        
        result = InServiceStatusTracker._get_status_from_db(self.user, self.project)
        
        self.assertIsNone(result)

    @patch('chats.apps.projects.usecases.status_service.cache')
    def test_update_status_cache(self, mock_cache):
        """Testa se _update_status_cache atualiza corretamente o cache"""
        status = CustomStatus.objects.create(
            user=self.user,
            status_type=self.status_type,
            is_active=True,
            project=self.project,
            break_time=0
        )
        
        InServiceStatusTracker._update_status_cache(self.user.id, self.project.uuid, status)
        
        timeout = InServiceStatusTracker.get_cache_timeout(self.project.uuid)
        keys = InServiceStatusTracker.get_cache_keys(self.user.id, self.project.uuid)
        
        mock_cache.set.assert_any_call(keys["status_id"], str(status.uuid), timeout)
        mock_cache.set.assert_any_call(keys["start_time"], status.created_on, timeout)

    @patch('chats.apps.projects.usecases.status_service.InServiceStatusTracker._get_status_from_cache')
    @patch('chats.apps.projects.usecases.status_service.InServiceStatusTracker._get_status_from_db')
    @patch('chats.apps.projects.usecases.status_service.InServiceStatusTracker._update_status_cache')
    def test_get_current_status_from_cache(self, mock_update_cache, mock_get_db, mock_get_cache):
        """Testa se get_current_status retorna o status do cache quando disponível"""
        status = MagicMock()
        mock_get_cache.return_value = (status, True)
        
        result, from_cache = InServiceStatusTracker.get_current_status(self.user, self.project)
        
        self.assertEqual(result, status)
        self.assertTrue(from_cache)
        mock_get_db.assert_not_called()
        mock_update_cache.assert_not_called()

    @patch('chats.apps.projects.usecases.status_service.InServiceStatusTracker._get_status_from_cache')
    @patch('chats.apps.projects.usecases.status_service.InServiceStatusTracker._get_status_from_db')
    @patch('chats.apps.projects.usecases.status_service.InServiceStatusTracker._update_status_cache')
    def test_get_current_status_from_db(self, mock_update_cache, mock_get_db, mock_get_cache):
        """Testa se get_current_status busca no banco e atualiza o cache quando não está no cache"""
        mock_get_cache.return_value = (None, False)
        status = MagicMock()
        mock_get_db.return_value = status
        
        result, from_cache = InServiceStatusTracker.get_current_status(self.user, self.project)
        
        self.assertEqual(result, status)
        self.assertFalse(from_cache)
        mock_get_db.assert_called_once()
        mock_update_cache.assert_called_once_with(self.user.id, self.project.uuid, status)

    @patch('chats.apps.projects.usecases.status_service.cache')
    @patch('chats.apps.projects.usecases.status_service.InServiceStatusTracker.get_current_status')
    def test_update_room_count_assigned_first_room(self, mock_get_status, mock_cache):
        """Testa se update_room_count cria um novo status quando é a primeira sala atribuída"""
        mock_cache.incr.return_value = 1
        mock_get_status.return_value = (None, False)
        
        with patch('chats.apps.projects.usecases.status_service.CustomStatus.objects.create') as mock_create:
            mock_status = MagicMock()
            mock_status.uuid = "test-uuid"
            mock_create.return_value = mock_status
            
            InServiceStatusTracker.update_room_count(self.user, self.project, "assigned")
            
            mock_create.assert_called_once()
            
            keys = InServiceStatusTracker.get_cache_keys(self.user.id, self.project.uuid)
            timeout = InServiceStatusTracker.get_cache_timeout(self.project.uuid)
            mock_cache.set.assert_any_call(keys["status_id"], str(mock_status.uuid), timeout)

    @patch('chats.apps.projects.usecases.status_service.cache')
    def test_update_room_count_closed_last_room(self, mock_cache):
        """Testa se update_room_count finaliza o status quando a última sala é fechada"""
       
        cache_values = {}
        keys = InServiceStatusTracker.get_cache_keys(self.user.id, self.project.pk)
        
        cache_values[keys["room_count"]] = 1 
        cache_values[keys["status_id"]] = "test-uuid"  
        cache_values[keys["start_time"]] = timezone.now() - timezone.timedelta(hours=1)  
        
        def mock_cache_get(key, default=None):
            return cache_values.get(key, default)
        
        mock_cache.get.side_effect = mock_cache_get
        mock_cache.decr.return_value = 0 
        
        with patch('chats.apps.projects.usecases.status_service.CustomStatus.objects.select_for_update') as mock_select:
            mock_queryset = MagicMock()
            mock_status = MagicMock()
            mock_status.is_active = True
            mock_select.return_value = mock_queryset
            mock_queryset.get.return_value = mock_status
            
            InServiceStatusTracker.update_room_count(self.user, self.project, "closed")
            
            mock_queryset.get.assert_called_once_with(uuid="test-uuid", is_active=True)
            
            self.assertFalse(mock_status.is_active)
            self.assertGreater(mock_status.break_time, 0)
            
            mock_status.save.assert_called_once_with(update_fields=['is_active', 'break_time'])
            
            mock_cache.delete.assert_any_call(keys["status_id"])
            mock_cache.delete.assert_any_call(keys["start_time"])