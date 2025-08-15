from rest_framework.settings import api_settings
from rest_framework.throttling import SimpleRateThrottle


class ExternalBaseThrottle(SimpleRateThrottle):
    """
    Base throttle para endpoints externos - SEMPRE autenticados
    """

    def get_rate(self):
        rates = api_settings.DEFAULT_THROTTLE_RATES or {}
        return rates.get(self.scope)

    def get_cache_key(self, request, view):
        if isinstance(request.user, str):
            ident = request.user
        else:
            ident = str(request.user.pk)
        return self.cache_format % {"scope": self.scope, "ident": ident}


class ExternalSecondRateThrottle(ExternalBaseThrottle):
    """Previne rajadas extremas - máximo por segundo"""

    scope = "external_second"


class ExternalMinuteRateThrottle(ExternalBaseThrottle):
    """Previne rajadas sustentadas - máximo por minuto"""

    scope = "external_minute"


class ExternalHourRateThrottle(ExternalBaseThrottle):
    """Limite geral por hora"""

    scope = "external_hour"


class ExternalAnonRateThrottle(ExternalBaseThrottle):
    """Rate limiting mais restritivo para requisições anônimas"""

    scope = "external_anon"


class ExternalCriticalRateThrottle(ExternalBaseThrottle):
    """Para endpoints como POST rooms com volume muito alto"""

    scope = "external_critical"
