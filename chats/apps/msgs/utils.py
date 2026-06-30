"""
Utilities for the ``msgs`` app.

The most important helper here is :func:`extract_wamid_core`, which extracts
the stable "core" of a WhatsApp Cloud API message id (WAMID).

Why this exists
---------------
A WAMID such as ``wamid.HBgMNTU4MjgyMDczMTc1FQIAERgSNzg2MzFG...`` is a base64
encoded payload built by Meta. Empirically, the **same logical message** can
be referenced by WAMIDs with **different prefixes/envelopes** depending on the
context in which Meta emits the id (for example, the WAMID returned by the
Cloud API when the message was created vs. the WAMID that arrives inside the
``context.id`` of a reply).

The wrapping bytes change, but the trailing message id bytes are stable. This
function decodes the base64 payload and returns the trailing hex of the
internal message id, which can then be used as a fallback key when an exact
``external_id`` match against :class:`ChatMessageReplyIndex` fails.

The function is intentionally defensive: any unexpected/non-WAMID input
returns ``None`` so callers can simply skip the fallback path.
"""

from __future__ import annotations

import base64
import logging
from typing import Optional

from django.conf import settings
from sentry_sdk import capture_exception
from weni.feature_flags.shortcuts import is_feature_active_for_attributes

logger = logging.getLogger(__name__)


_WAMID_PREFIX = "wamid."

# Protobuf-like field markers that immediately precede the trailing message
# id bytes inside the decoded WAMID payload. They were derived from real
# WAMIDs observed in production for both ``wamid.HBgM`` (contact-origin) and
# ``wamid.HBgT`` (agent-origin) envelopes.
_WAMID_TRAILER_MARKERS = (
    bytes([0x12, 0x18, 0x16]),
    bytes([0x11, 0x18, 0x12]),
)


def extract_wamid_core(wamid: Optional[str]) -> Optional[str]:
    """Return the stable hex core of a WAMID, or ``None`` when not extractable.

    Returns ``None`` for ``None``, empty strings, non-string values, ids that
    do not start with the ``wamid.`` prefix, or payloads whose decoded bytes
    do not contain the expected trailer markers. Failures are logged at WARNING
    level and never raise, because this helper is used inside hot paths
    (serializers, consumers) where a malformed WAMID must not break the flow.
    """

    if not wamid or not isinstance(wamid, str):
        return None

    if not wamid.startswith(_WAMID_PREFIX):
        return None

    encoded = wamid[len(_WAMID_PREFIX):]
    encoded += "=" * ((-len(encoded)) % 4)

    try:
        raw = base64.b64decode(encoded)
    except (ValueError, base64.binascii.Error):
        logger.warning(
            "Failed to base64-decode WAMID payload",
            extra={"wamid_prefix": wamid[:32]},
        )
        return None

    for marker in _WAMID_TRAILER_MARKERS:
        idx = raw.rfind(marker)
        if idx != -1:
            core_bytes = raw[idx + len(marker):]
            if core_bytes:
                return core_bytes.hex().upper()

    return None


def is_reply_core_fallback_active(project_uuid: Optional[str]) -> bool:
    """Return whether the WAMID core fallback is enabled for ``project_uuid``.

    Centralized wrapper around the feature flag SDK so all call sites
    (viewsets and serializers) share the same safety net: a missing or
    falsy ``project_uuid`` short-circuits to ``False``, and any failure
    talking to the flag service is captured on Sentry/logger and degrades
    to ``False`` so the request stays on the legacy/exact-match path.
    Never raises.
    """

    if not project_uuid:
        return False

    try:
        return is_feature_active_for_attributes(
            settings.REPLY_CORE_FALLBACK_FEATURE_FLAG_KEY,
            {"projectUUID": str(project_uuid)},
        )
    except Exception as error:
        capture_exception(error)
        logger.error(
            "Error checking if reply core fallback feature flag is active: %s",
            error,
        )
        return False
