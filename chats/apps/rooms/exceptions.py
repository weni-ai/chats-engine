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
