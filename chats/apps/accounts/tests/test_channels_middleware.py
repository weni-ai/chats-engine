from unittest.mock import patch, Mock, AsyncMock
from datetime import datetime, timedelta
from django.test import TestCase, override_settings
import asyncio
import time

from chats.apps.accounts.authentication.channels.middleware import (
    CircuitBreaker,
    CircuitState,
    TokenCache,
)


class TestCircuitBreaker(TestCase):
    """Testes para o Circuit Breaker."""
    
    def test_initial_state_is_closed(self):
        """Circuit breaker inicia no estado CLOSED."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        self.assertEqual(cb.state, CircuitState.CLOSED)
    
    def test_circuit_opens_after_threshold(self):
        """Circuit abre após atingir threshold de falhas."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        
        def failing_func():
            raise Exception("Test failure")
        
        # Simula 3 falhas
        for _ in range(3):
            with self.assertRaises(Exception):
                cb.call(failing_func)
        
        self.assertEqual(cb.state, CircuitState.OPEN)
    
    def test_circuit_breaker_blocks_when_open(self):
        """Circuit breaker bloqueia chamadas quando aberto."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60)
        
        # Abre o circuit
        with self.assertRaises(Exception):
            cb.call(lambda: 1/0)
        
        # Tenta chamar com circuit aberto
        with self.assertRaises(Exception) as cm:
            cb.call(lambda: "success")
        
        self.assertIn("Circuit breaker is OPEN", str(cm.exception))
    
    def test_success_resets_failure_count(self):
        """Sucesso reseta contador de falhas."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        
        # Duas falhas
        for _ in range(2):
            with self.assertRaises(Exception):
                cb.call(lambda: 1/0)
        
        # Um sucesso deve resetar
        result = cb.call(lambda: "success")
        self.assertEqual(result, "success")
        self.assertEqual(cb._failure_count, 0)
        
        # Mais duas falhas não devem abrir (precisaria de 3)
        for _ in range(2):
            with self.assertRaises(Exception):
                cb.call(lambda: 1/0)
        
        self.assertEqual(cb.state, CircuitState.CLOSED)
    
    @patch('chats.apps.accounts.authentication.channels.middleware.datetime')
    def test_half_open_transition_after_timeout(self, mock_datetime):
        """Transição para HALF_OPEN após recovery timeout."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60)
        
        # Configure o tempo inicial
        initial_time = datetime.now()
        mock_datetime.now.return_value = initial_time
        
        # Abre o circuit
        with self.assertRaises(Exception):
            cb.call(lambda: 1/0)
        
        self.assertEqual(cb.state, CircuitState.OPEN)
        
        # Avança o tempo além do recovery timeout
        mock_datetime.now.return_value = initial_time + timedelta(seconds=61)
        
        # Estado deve ser HALF_OPEN agora
        self.assertEqual(cb.state, CircuitState.HALF_OPEN)
    
    def test_half_open_success_closes_circuit(self):
        """Sucesso em HALF_OPEN fecha o circuit."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        
        # Abre o circuit
        with self.assertRaises(Exception):
            cb.call(lambda: 1/0)
        
        # Espera transição para HALF_OPEN
        time.sleep(0.2)
        
        # Sucesso deve fechar o circuit
        result = cb.call(lambda: "success")
        self.assertEqual(result, "success")
        self.assertEqual(cb.state, CircuitState.CLOSED)
    
    def test_half_open_failure_reopens_circuit(self):
        """Falha em HALF_OPEN reabre o circuit."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        
        # Abre o circuit
        with self.assertRaises(Exception):
            cb.call(lambda: 1/0)
        
        # Espera transição para HALF_OPEN
        time.sleep(0.2)
        self.assertEqual(cb.state, CircuitState.HALF_OPEN)
        
        # Falha deve reabrir
        with self.assertRaises(Exception):
            cb.call(lambda: 1/0)
        
        self.assertEqual(cb._state, CircuitState.OPEN)
    
    def test_async_call_success(self):
        """Testa chamada assíncrona com sucesso."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        
        async def async_success():
            return "async result"
        
        # Executa teste assíncrono
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(cb.async_call(async_success))
        loop.close()
        
        self.assertEqual(result, "async result")
    
    def test_async_call_failure_opens_circuit(self):
        """Testa chamada assíncrona com falha abre circuit."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60)
        
        async def async_failure():
            raise Exception("Async failure")
        
        # Executa teste assíncrono
        loop = asyncio.new_event_loop()
        with self.assertRaises(Exception):
            loop.run_until_complete(cb.async_call(async_failure))
        loop.close()
        
        self.assertEqual(cb.state, CircuitState.OPEN)
    
    def test_custom_expected_exceptions(self):
        """Testa que apenas exceções esperadas contam como falha."""
        cb = CircuitBreaker(
            failure_threshold=2, 
            recovery_timeout=60,
            expected_exception=(ValueError,)
        )
        
        # RuntimeError não deve contar
        with self.assertRaises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("Not counted")))
        
        self.assertEqual(cb._failure_count, 0)
        
        # ValueError deve contar
        with self.assertRaises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("Counted")))
        
        self.assertEqual(cb._failure_count, 1)


class TestTokenCache(TestCase):
    """Testes para o cache de tokens."""
    
    @override_settings(TOKEN_CACHE_TTL=900)
    def test_cache_key_generation(self):
        """Testa geração de chave de cache para token."""
        token = "abc123xyz"
        expected = "ws_auth_token:abc123xyz"
        
        self.assertEqual(TokenCache.get_cache_key(token), expected)
    
    @patch('chats.apps.accounts.authentication.channels.middleware.cache')
    def test_get_user_from_cache(self, mock_cache):
        """Testa busca de usuário do cache de token."""
        token = "abc123"
        cached_user = Mock()
        mock_cache.get.return_value = cached_user
        
        result = TokenCache.get_user(token)
        
        self.assertEqual(result, cached_user)
        mock_cache.get.assert_called_once_with("ws_auth_token:abc123")
    
    @patch('chats.apps.accounts.authentication.channels.middleware.cache')
    def test_set_user_to_cache(self, mock_cache):
        """Testa armazenamento de usuário no cache."""
        token = "abc123"
        user = Mock()
        
        TokenCache.set_user(token, user)
        
        mock_cache.set.assert_called_once_with(
            "ws_auth_token:abc123", 
            user, 
            TokenCache.CACHE_TTL
        )
    
    @patch('chats.apps.accounts.authentication.channels.middleware.cache')
    def test_invalidate_cache(self, mock_cache):
        """Testa invalidação de cache."""
        token = "abc123"
        
        TokenCache.invalidate(token)
        
        mock_cache.delete.assert_called_once_with("ws_auth_token:abc123")