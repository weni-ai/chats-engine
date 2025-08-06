from django.test import TestCase
from django.contrib.auth import get_user_model

from chats.apps.accounts.authentication.drf.backends import UserEmailCache

User = get_user_model()


class TestAuthenticationIntegration(TestCase):
    """Testes de integração do sistema de autenticação com cache."""
    
    def test_cache_invalidation_on_user_update(self):
        """Testa que cache é invalidado quando usuário é atualizado."""
        # Cria usuário
        user = User.objects.create(email='test@example.com', first_name='Original')
        
        # Armazena no cache
        UserEmailCache.set_user(user.email, user)
        
        # Verifica que está em cache
        cached = UserEmailCache.get_user(user.email)
        self.assertIsNotNone(cached)
        
        # Invalida cache
        UserEmailCache.invalidate(user.email)
        
        # Verifica que não está mais em cache
        cached = UserEmailCache.get_user(user.email)
        self.assertIsNone(cached)