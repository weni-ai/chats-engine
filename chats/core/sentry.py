"""
Sentry helpers: filter expected/noisy events so they stay in logs only.
"""

from __future__ import annotations

import re
from typing import Optional

_IGNORED_EXCEPTION_NAMES = frozenset(
    {
        "Disconnected",
        "ConnectionClosed",
        "ConnectionClosedError",
        "ConnectionClosedOK",
        "WorkerLostError",
    }
)

_IGNORED_MESSAGE_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"Attempt to send on a closed protocol",
        r"Closed rooms can't receive messages",
        r"after 24h from the last contact message",
        r"more than one active status per project",
        r"is not a valid UUID",
        r"Worker exited prematurely: signal 15 \(SIGTERM\)",
        r"ServiceUnavailableException",
        r"InternalServerException",
        r"ThrottlingException",
        r"ModelTimeoutException",
        r"growthbook",
        r"accounts\.weni\.ai",
        r"Error getting feature flags definitions from GrowthBook",
    )
)

_EXPECTED_VALIDATION_DETAILS = (
    "Closed rooms can't receive messages",
    "You can't send messages after 24h from the last contact message",
    "you can't have more than one active status per project",
)


def is_closed_websocket_error(exc: BaseException) -> bool:
    """True when the client already closed the WS connection."""
    if type(exc).__name__ in _IGNORED_EXCEPTION_NAMES:
        return True
    return "closed protocol" in str(exc).lower()


def is_expected_validation_error(exc: BaseException) -> bool:
    """True for known business-rule ValidationErrors (not product bugs)."""
    detail = str(exc)
    return any(expected in detail for expected in _EXPECTED_VALIDATION_DETAILS)


def _event_text(event: dict, exc_value: Optional[BaseException]) -> str:
    parts = []
    if event.get("message"):
        parts.append(str(event["message"]))
    if exc_value is not None:
        parts.append(str(exc_value))
    for entry in event.get("exception", {}).get("values") or []:
        if entry.get("type"):
            parts.append(str(entry["type"]))
        if entry.get("value"):
            parts.append(str(entry["value"]))
    return " ".join(parts)


def sentry_before_send(event: dict, hint: dict) -> Optional[dict]:
    """
    Drop expected noise from Sentry. Real bugs must still pass through.
    """
    exc_info = hint.get("exc_info")
    exc_type = None
    exc_value = None
    if exc_info:
        exc_type, exc_value, _ = exc_info
        name = getattr(exc_type, "__name__", "")
        if name in _IGNORED_EXCEPTION_NAMES:
            return None
        if is_expected_validation_error(exc_value):
            return None
        if is_closed_websocket_error(exc_value):
            return None

    text = _event_text(event, exc_value)
    if any(pattern.search(text) for pattern in _IGNORED_MESSAGE_PATTERNS):
        return None

    return event
