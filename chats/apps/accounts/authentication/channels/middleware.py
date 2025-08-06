import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, Any
from urllib.error import HTTPError as UrllibHTTPError
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from requests.exceptions import HTTPError as RequestsHTTPError
from rest_framework.authtoken.models import Token

from chats.apps.accounts.authentication.drf.backends import (
    WeniOIDCAuthenticationBackend,
)

LOGGER = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """
    Circuit Breaker para proteger contra falhas em cascata.
    
    Estados:
    - CLOSED: Normal, permite todas as chamadas
    - OPEN: Muitas falhas, bloqueia chamadas
    - HALF_OPEN: Testa se o serviço voltou
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: tuple = (Exception,)
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self._failure_count = 0
        self._last_failure_time = None
        self._state = CircuitState.CLOSED
    
    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if self._last_failure_time and \
               (datetime.now() - self._last_failure_time).total_seconds() > self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
        return self._state
    
    def call(self, func, *args, **kwargs):
        """Executa a função protegida pelo circuit breaker."""
        if self.state == CircuitState.OPEN:
            raise Exception("Circuit breaker is OPEN - Service unavailable")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    async def async_call(self, func, *args, **kwargs):
        """Executa função assíncrona protegida pelo circuit breaker."""
        if self.state == CircuitState.OPEN:
            raise Exception("Circuit breaker is OPEN - Service unavailable")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _on_success(self):
        """Reset ao receber sucesso."""
        self._failure_count = 0
        self._state = CircuitState.CLOSED
    
    def _on_failure(self):
        """Incrementa falhas e potencialmente abre o circuit."""
        self._failure_count += 1
        self._last_failure_time = datetime.now()
        
        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            LOGGER.warning(
                f"Circuit breaker opened after {self._failure_count} failures"
            )


class TokenCache:
    """
    Cache in-memory para tokens de autenticação (CACHE 1).
    Cacheia: Token → User completo
    """
    
    CACHE_PREFIX = "ws_auth_token:"
    CACHE_TTL = settings.TOKEN_CACHE_TTL  # Vem do settings/env
    
    @classmethod
    def get_cache_key(cls, token_key: str) -> str:
        return f"{cls.CACHE_PREFIX}{token_key}"
    
    @classmethod
    def get_user(cls, token_key: str) -> Optional[Any]:
        """Busca usuário do cache."""
        if not token_key:
            return None
        
        cache_key = cls.get_cache_key(token_key)
        cached_user = cache.get(cache_key)
        
        if cached_user:
            LOGGER.debug(f"Token cache HIT for: {token_key[:8]}...")
        else:
            LOGGER.debug(f"Token cache MISS for: {token_key[:8]}...")
        
        return cached_user
    
    @classmethod
    def set_user(cls, token_key: str, user: Any) -> None:
        """Armazena usuário no cache."""
        if not token_key or not user:
            return
        
        cache_key = cls.get_cache_key(token_key)
        cache.set(cache_key, user, cls.CACHE_TTL)
        LOGGER.debug(f"Token cached for: {token_key[:8]}...")
    
    @classmethod
    def invalidate(cls, token_key: str) -> None:
        """Remove token do cache."""
        if not token_key:
            return
        
        cache_key = cls.get_cache_key(token_key)
        cache.delete(cache_key)


# Circuit breakers com configurações do settings
db_circuit_breaker = CircuitBreaker(
    failure_threshold=settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
    recovery_timeout=settings.CIRCUIT_BREAKER_RECOVERY_TIMEOUT,
    expected_exception=(Exception,)
)

keycloak_circuit_breaker = CircuitBreaker(
    failure_threshold=settings.KEYCLOAK_CIRCUIT_BREAKER_THRESHOLD,
    recovery_timeout=settings.KEYCLOAK_CIRCUIT_BREAKER_TIMEOUT,
    expected_exception=(UrllibHTTPError, RequestsHTTPError, Exception)
)


@database_sync_to_async
def get_user(token_key):
    """Busca usuário pelo token com circuit breaker."""
    def _get_from_db():
        try:
            token = Token.objects.get(key=token_key)
            return token.user
        except Token.DoesNotExist:
            return AnonymousUser()
    
    return db_circuit_breaker.call(_get_from_db)


@database_sync_to_async
def get_keycloak_user(token_key):
    """Busca usuário no Keycloak com circuit breaker."""
    def _get_from_keycloak():
        auth = WeniOIDCAuthenticationBackend()
        return auth.get_or_create_user(token_key, None, None)
    
    return keycloak_circuit_breaker.call(_get_from_keycloak)


class TokenAuthMiddleware(BaseMiddleware):
    """
    Middleware de autenticação com Circuit Breaker e Cache.
    
    Features:
    - Cache in-memory de tokens válidos (5 min TTL) - CACHE 1
    - Circuit breaker para falhas de DB/Keycloak
    - Fail-fast quando serviços estão down
    - Métricas de cache hit/miss
    """
    
    def __init__(self, inner):
        super().__init__(inner)
        self._auth_failures = 0
        self._cache_hits = 0
        self._cache_misses = 0
        self._last_metrics_log = time.time()
    
    async def __call__(self, scope, receive, send):
        try:
            query_params = parse_qs(scope["query_string"].decode())
            scope["query_params"] = query_params
            token_key = query_params.get("Token", [None])[0]
        except (ValueError, TypeError):
            token_key = None
        
        # CACHE 1: Tenta buscar do cache de tokens primeiro
        user = None
        if token_key:
            user = TokenCache.get_user(token_key)
            if user:
                self._cache_hits += 1
                LOGGER.debug(f"Token cache HIT - User: {user.email}")
            else:
                self._cache_misses += 1
        
        # Se não encontrou no cache, busca do backend
        if user is None and token_key:
            try:
                if settings.OIDC_ENABLED:
                    user = await keycloak_circuit_breaker.async_call(
                        get_keycloak_user, token_key
                    )
                else:
                    user = await db_circuit_breaker.async_call(
                        get_user, token_key
                    )
                
                # Armazena no CACHE 1 se autenticação bem-sucedida
                if user and not isinstance(user, AnonymousUser):
                    TokenCache.set_user(token_key, user)
                
            except Exception as e:
                self._auth_failures += 1
                LOGGER.error(f"Authentication failed: {str(e)}")
                user = AnonymousUser()
        
        # Define usuário no scope
        scope["user"] = user if user else AnonymousUser()
        
        return await super().__call__(scope, receive, send)
