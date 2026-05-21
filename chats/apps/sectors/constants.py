from django.utils.translation import gettext_lazy as _


# Default warning time in seconds (10 minutes)
DEFAULT_MESSAGE_TIMEOUT_TIME = 600

# Default closure time in seconds (1 minute)
DEFAULT_CLOSE_ROOM_TIMEOUT_TIME = 60


def get_default_inactivity_timeout() -> dict:
    """
    Returns the default values for the sector's `inactivity_timeout` JSON field.

    Used when a sector has not configured the inactivity feature yet, so the API
    can return a sane shape to the frontend (and so any consumer — task, usecase,
    serializer — reuses the same defaults).

    Times are stored in seconds.
    """
    return {
        "is_message_timeout_enabled": False,
        "message_timeout_text": str(
            _(
                "Hi! Are you still there? "
                "If there's no response, this conversation will be closed soon."
            )
        ),
        "message_timeout_time": DEFAULT_MESSAGE_TIMEOUT_TIME,
        "is_close_room_enabled": False,
        "close_room_message_text": str(
            _(
                "We're closing this conversation due to inactivity. "
                "Get in touch again if needed."
            )
        ),
        "close_room_timeout_time": DEFAULT_CLOSE_ROOM_TIMEOUT_TIME,
    }
