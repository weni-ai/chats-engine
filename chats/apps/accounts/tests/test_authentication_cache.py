from unittest.mock import patch, Mock, MagicMock
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.cache import cache

from chats.apps.accounts.authentication.drf.backends import (
    UserEmailCache, 
    WeniOIDCAuthenticationBackend
)

User = get_user_model()


class TestUserEmailCache(TestCase):
    """Testes para o cache de usuários por email."""
    
    def setUp(self):
        """Limpa cache antes de cada teste."""
        cache.clear()
    
    @override_settings(USER_EMAIL_CACHE_TTL=1800)
    def test_cache_key_generation(self):
        """Testa geração de chave de cache normalizada."""
        email = "User@Example.COM"
        expected_key = "user:email:user@example.com"
        
        self.assertEqual(UserEmailCache.get_cache_key(email), expected_key)
    
    @patch('chats.apps.accounts.authentication.drf.backends.cache')
    def test_get_user_cache_hit(self, mock_cache):
        """Testa busca de usuário com cache HIT."""
        email = "test@example.com"
        cached_user = Mock(email=email)
        mock_cache.get.return_value = cached_user
        
        result = UserEmailCache.get_user(email)
        
        self.assertEqual(result, cached_user)
        mock_cache.get.assert_called_once_with("user:email:test@example.com")
    
    @patch('chats.apps.accounts.authentication.drf.backends.cache')
    def test_get_user_cache_miss(self, mock_cache):
        """Testa busca de usuário com cache MISS."""
        email = "test@example.com"
        mock_cache.get.return_value = None
        
        result = UserEmailCache.get_user(email)
        
        self.assertIsNone(result)
        mock_cache.get.assert_called_once()
    
    def test_get_user_with_empty_email(self):
        """Testa que email vazio retorna None sem consultar cache."""
        result = UserEmailCache.get_user("")
        self.assertIsNone(result)
        
        result = UserEmailCache.get_user(None)
        self.assertIsNone(result)
    
    @patch('chats.apps.accounts.authentication.drf.backends.cache')
    @patch('chats.apps.accounts.authentication.drf.backends.LOGGER')
    def test_set_user_logs_correctly(self, mock_logger, mock_cache):
        """Testa que set_user registra logs corretamente."""
        email = "test@example.com"
        user = Mock(email=email)
        
        UserEmailCache.set_user(email, user)
        
        mock_logger.debug.assert_called_with(f"User cached for email: {email}")
        mock_cache.set.assert_called_once()
    
    def test_cache_invalidation(self):
        """Testa invalidação de cache."""
        # Cria e cacheia usuário
        user = User.objects.create(email='cache_test@example.com')
        UserEmailCache.set_user(user.email, user)
        
        # Verifica que está em cache
        cached = UserEmailCache.get_user(user.email)
        self.assertEqual(cached.email, user.email)
        
        # Invalida
        UserEmailCache.invalidate(user.email)
        
        # Verifica que foi removido
        cached = UserEmailCache.get_user(user.email)
        self.assertIsNone(cached)
    
    def test_concurrent_cache_access(self):
        """Testa acesso concorrente ao cache."""
        from threading import Thread
        
        email = "concurrent@example.com"
        user = User.objects.create(email=email)
        results = []
        
        def cache_operation():
            UserEmailCache.set_user(email, user)
            cached = UserEmailCache.get_user(email)
            results.append(cached)
        
        # Executa 10 threads simultaneamente
        threads = [Thread(target=cache_operation) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Todos devem ter obtido o mesmo usuário
        self.assertEqual(len(results), 10)
        self.assertTrue(all(r.email == email for r in results))


@override_settings(
    OIDC_OP_TOKEN_ENDPOINT='http://fake-oidc.com/token',
    OIDC_OP_USER_ENDPOINT='http://fake-oidc.com/user',
    OIDC_OP_JWKS_ENDPOINT='http://fake-oidc.com/jwks',
    OIDC_RP_CLIENT_ID='test-client-id',
    OIDC_RP_CLIENT_SECRET='test-client-secret'
)
class TestWeniOIDCAuthenticationBackend(TestCase):
    """Testes para o backend OIDC com cache."""
    
    def setUp(self):
        self.backend = WeniOIDCAuthenticationBackend()
        self.claims = {
            'email': 'test@example.com',
            'given_name': 'Test',
            'family_name': 'User',
            'preferred_username': 'testuser'
        }
        cache.clear()
    
    @patch('chats.apps.accounts.authentication.drf.backends.UserEmailCache.get_user')
    @patch('chats.apps.accounts.authentication.drf.backends.check_module_permission')
    def test_create_user_cache_hit(self, mock_check_perm, mock_get_user):
        """Testa create_user quando usuário está em cache."""
        cached_user = Mock(
            email='test@example.com',
            first_name='Old',
            last_name='Name'
        )
        cached_user.save = Mock()
        mock_get_user.return_value = cached_user
        
        result = self.backend.create_user(self.claims)
        
        self.assertEqual(result, cached_user)
        self.assertEqual(cached_user.first_name, 'Test')
        self.assertEqual(cached_user.last_name, 'User')
        cached_user.save.assert_called_once_with(update_fields=['first_name', 'last_name'])
        mock_check_perm.assert_called_once_with(self.claims, cached_user)
    
    @patch('chats.apps.accounts.authentication.drf.backends.UserEmailCache.get_user')
    @patch('chats.apps.accounts.authentication.drf.backends.UserEmailCache.set_user')
    @patch('chats.apps.accounts.authentication.drf.backends.check_module_permission')
    def test_create_user_cache_miss(self, mock_check_perm, mock_set_user, mock_get_user):
        """Testa create_user quando usuário NÃO está em cache."""
        mock_get_user.return_value = None
        
        # Mock do User.objects.get_or_create
        with patch.object(User.objects, 'get_or_create') as mock_get_or_create:
            new_user = Mock(
                email='test@example.com',
                first_name='',
                last_name=''
            )
            new_user.save = Mock()
            mock_get_or_create.return_value = (new_user, True)
            
            result = self.backend.create_user(self.claims)
            
            # Verifica que usuário foi criado
            self.assertEqual(result, new_user)
            self.assertEqual(new_user.first_name, 'Test')
            self.assertEqual(new_user.last_name, 'User')
            
            # Verifica que foi salvo no cache
            mock_set_user.assert_called_once_with('test@example.com', new_user)
    
    def test_create_user_no_update_when_data_unchanged(self):
        """Testa que não há update desnecessário quando dados não mudam."""
        # Cria usuário com dados corretos
        user = User.objects.create(
            email='nochange@example.com',
            first_name='Test',
            last_name='User'
        )
        UserEmailCache.set_user(user.email, user)
        
        claims = {
            'email': 'nochange@example.com',
            'given_name': 'Test',
            'family_name': 'User',
            'preferred_username': 'testuser'
        }
        
        with patch.object(user, 'save') as mock_save:
            result = self.backend.create_user(claims)
            
            # save() não deve ser chamado se nada mudou
            mock_save.assert_not_called()
            self.assertEqual(result.email, user.email)