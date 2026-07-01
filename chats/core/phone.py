import logging
import re
from typing import Optional, Tuple

from django.conf import settings
from django.db.models import Q
from weni.feature_flags.shortcuts import (
    is_feature_active,
    is_feature_active_for_attributes,
)

LOGGER = logging.getLogger(__name__)

_BR_PHONE_MIN_DIGITS = 8
_BR_PHONE_MAX_DIGITS = 13
_BR_COUNTRY_CODE = "55"
_WHATSAPP_SCHEME = "whatsapp:"


def _parse_br_phone_digits(term: str) -> Optional[Tuple[str, str]]:
    """
    Extract DDD and 8-digit base from a Brazilian mobile search term.

    Accepts numbers with or without country code (55) and with or without
    the optional 9th digit. Returns (ddd, base8) or None when the term does
    not look like a Brazilian mobile number.

    Numbers with 12 or 13 digits that do not start with the BR country
    code (``55``) are considered foreign and rejected, since the country
    code is the only reliable signal at that length.
    """
    digits = re.sub(r"\D", "", term)
    if len(digits) < _BR_PHONE_MIN_DIGITS or len(digits) > _BR_PHONE_MAX_DIGITS:
        return None
    if digits.startswith(_BR_COUNTRY_CODE) and len(digits) in (12, 13):
        digits = digits[2:]
    elif len(digits) in (12, 13):
        return None
    if len(digits) not in (8, 9, 10, 11):
        return None
    base8 = digits[-8:]
    rest = digits[:-8]
    ddd = rest[:2] if len(rest) >= 2 else ""
    return ddd, base8


def is_ninth_digit_search_enabled(
    user_email: Optional[str] = None,
    project_uuid: Optional[str] = None,
) -> bool:
    if not project_uuid:
        return False
    try:
        if user_email:
            return is_feature_active(
                settings.NINTH_DIGIT_SEARCH_FEATURE_FLAG_KEY,
                user_email,
                str(project_uuid),
            )
        return is_feature_active_for_attributes(
            settings.NINTH_DIGIT_SEARCH_FEATURE_FLAG_KEY,
            {"projectUUID": str(project_uuid)},
        )
    except Exception:
        LOGGER.warning(
            "Failed to evaluate ninth-digit search feature flag for project %s",
            project_uuid,
            exc_info=True,
        )
        return False


def ninth_digit_search_enabled_from_request(request) -> bool:
    if request is None:
        return False
    cached = getattr(request, "_ninth_digit_search_flag", None)
    if cached is not None:
        return cached
    params = getattr(request, "query_params", None) or getattr(request, "GET", {})
    project_uuid = params.get("project")
    user = getattr(request, "user", None)
    user_email = (
        getattr(user, "email", None)
        if getattr(user, "is_authenticated", False)
        else None
    )
    result = is_ninth_digit_search_enabled(
        user_email=user_email,
        project_uuid=project_uuid,
    )
    request._ninth_digit_search_flag = result
    return result


def phone_urn_q(term: str, field: str = "urn") -> Optional[Q]:
    """
    Build a combined URN filter that matches Brazilian mobile numbers with
    or without the 9th digit in a single query.

    Example: searching ``992126050`` matches both ``whatsapp:5584992126050``
    and ``whatsapp:558492126050``.

    When a DDD is present in the term, the filter is built from the two
    exact URN prefixes to avoid false positives across different DDDs or
    URNs that incidentally contain the same 8-digit suffix. When no DDD
    is provided, the filter falls back to a scope restricted to Brazilian
    numbers (``whatsapp:55``) that end with the 8-digit suffix.
    """
    parsed = _parse_br_phone_digits(term)
    if parsed is None:
        return None
    ddd, base8 = parsed
    if ddd:
        without_nine = f"{_WHATSAPP_SCHEME}{_BR_COUNTRY_CODE}{ddd}{base8}"
        with_nine = f"{_WHATSAPP_SCHEME}{_BR_COUNTRY_CODE}{ddd}9{base8}"
        return Q(**{f"{field}__startswith": without_nine}) | Q(
            **{f"{field}__startswith": with_nine}
        )
    return Q(**{f"{field}__startswith": f"{_WHATSAPP_SCHEME}{_BR_COUNTRY_CODE}"}) & Q(
        **{f"{field}__endswith": base8}
    )


def build_urn_lookup_q(
    term: str,
    field: str = "urn",
    lookup: str = "icontains",
    use_unaccent: bool = False,
    ninth_digit_enabled: bool = False,
) -> Q:
    """URN lookup with 9th-digit awareness and a fallback substring match."""
    phone_q = phone_urn_q(term, field=field) if ninth_digit_enabled else None
    lookup_key = (
        f"{field}__unaccent__{lookup}" if use_unaccent else f"{field}__{lookup}"
    )
    default_q = Q(**{lookup_key: term})
    return phone_q | default_q if phone_q else default_q
