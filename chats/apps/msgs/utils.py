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

# After the envelope (phone / LID), the internal message id is encoded as:
#
#     [tag 0x11|0x12]  0x18  [length N]  [N hex-ASCII chars]  [optional 0x00]
#
# The third byte is the **length of the id**, not a fixed magic. Meta has
# already emitted N in {18, 20, 22, 32}; hard-coding those values kept
# breaking every time a new id size appeared (e.g. contact self-reply with
# ``HBgU`` / length 20). Parsing the length byte covers current and future
# sizes without another deploy per envelope.
_WAMID_ID_TAGS = (0x11, 0x12)
_WAMID_LENGTH_FIELD = 0x18
_WAMID_MIN_ID_LEN = 8
_WAMID_MAX_ID_LEN = 64
_WAMID_HEX_ALPHABET = b"0123456789ABCDEFabcdef"


def extract_wamid_core(wamid: Optional[str]) -> Optional[str]:
    """Return the stable hex core of a WAMID, or ``None`` when not extractable.

    Returns ``None`` for ``None``, empty strings, non-string values, ids that
    do not start with the ``wamid.`` prefix, or payloads whose decoded bytes
    do not contain a recognizable id trailer. Failures are logged at WARNING
    level and never raise, because this helper is used inside hot paths
    (serializers, consumers) where a malformed WAMID must not break the flow.
    """

    if not wamid or not isinstance(wamid, str):
        return None

    if not wamid.startswith(_WAMID_PREFIX):
        return None

    encoded = wamid[len(_WAMID_PREFIX) :]
    encoded += "=" * ((-len(encoded)) % 4)

    try:
        raw = base64.b64decode(encoded)
    except (ValueError, base64.binascii.Error):
        logger.warning(
            "Failed to base64-decode WAMID payload",
            extra={"wamid_prefix": wamid[:32]},
        )
        return None

    # Scan from the end: the message id trailer sits after the envelope.
    for i in range(len(raw) - 3, -1, -1):
        if raw[i] not in _WAMID_ID_TAGS:
            continue
        if raw[i + 1] != _WAMID_LENGTH_FIELD:
            continue

        length = raw[i + 2]
        if not (_WAMID_MIN_ID_LEN <= length <= _WAMID_MAX_ID_LEN):
            continue

        start = i + 3
        end = start + length
        if end > len(raw):
            continue

        id_bytes = raw[start:end]
        if not id_bytes or any(b not in _WAMID_HEX_ALPHABET for b in id_bytes):
            continue

        # Preserve the historical core format (id bytes + trailing NUL when
        # present) so values already stored in ``external_id_core`` keep
        # matching without a rewrite of every row.
        if end < len(raw) and raw[end] == 0x00:
            end += 1

        return raw[start:end].hex().upper()

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
