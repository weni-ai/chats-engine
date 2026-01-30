from typing import List

from django.conf import settings

from django.db.models import QuerySet


def get_vtex_internal_domains_with_at_symbol() -> List[str]:
    return ["@" + domain for domain in settings.VTEX_INTERNAL_DOMAINS]


def is_vtex_internal_domain(email: str) -> bool:
    """
    Verify if the email belongs to a VTEX internal domain.
    """
    if not email:
        return False

    domains = get_vtex_internal_domains_with_at_symbol()

    return any(email.endswith(domain) for domain in domains)


def exclude_vtex_internal_domains(
    queryset: QuerySet, email_field: str = "email"
) -> QuerySet:
    """
    Exclude users with VTEX internal domains from the queryset.
    """

    email_field = email_field + "__endswith"

    domains = get_vtex_internal_domains_with_at_symbol()

    for domain in domains:
        queryset = queryset.exclude(**{email_field: domain})

    return queryset
