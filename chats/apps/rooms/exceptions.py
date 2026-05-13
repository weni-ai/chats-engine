from django.conf import settings
from django.core.exceptions import ValidationError


class MaxPinRoomLimitReachedError(ValidationError):
    """
    Raised when a user tries to pin a room and the limit per user is reached.
    """

    def __init__(self, message="Max pin room limit reached", code="max_pin_limit"):
        super().__init__(message, code)

    def to_dict(self) -> dict:
        """
        Returns a dictionary representation of the error.
        """
        return {
            "code": self.code,
            "message": self.message,
            "params": {"limit": settings.MAX_ROOM_PINS_LIMIT},
        }


class RoomIsNotActiveError(ValidationError):
    def __init__(self, message="Room is not active", code="room_is_not_active"):
        super().__init__(message, code)

    def to_dict(self) -> dict:
        """
        Returns a dictionary representation of the error.
        """
        return {"code": self.code, "message": self.message}


class FlowsTicketerNotFoundError(Exception):
    """
    Raised when no ticketer is found in Flows for a given sector.
    """

    def __init__(self, sector_uuid: str, message: str = ""):
        self.sector_uuid = sector_uuid
        self.message = (
            message
            or f"No ticketer found in Flows for sector {sector_uuid}"
        )
        super().__init__(self.message)


class FlowsChangeTicketerError(Exception):
    """
    Raised when the Flows ticket_actions/change_ticketer call fails.
    """

    def __init__(
        self,
        ticket_uuids: list,
        ticketer_uuid: str,
        status_code: int = None,
        response_content: str = "",
        message: str = "",
    ):
        self.ticket_uuids = ticket_uuids
        self.ticketer_uuid = ticketer_uuid
        self.status_code = status_code
        self.response_content = response_content
        self.message = message or (
            f"Failed to change ticketer to {ticketer_uuid} for tickets "
            f"{ticket_uuids} (status={status_code}): {response_content}"
        )
        super().__init__(self.message)
