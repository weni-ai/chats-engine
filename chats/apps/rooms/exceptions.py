from django.core.exceptions import ValidationError


class MaxPinRoomLimitReachedError(ValidationError):
    """
    Raised when a user tries to pin a room and the limit per user is reached.
    """

    def __init__(self, message="Max pin room limit reached", code="max_pin_limit"):
        super().__init__(message, code)
