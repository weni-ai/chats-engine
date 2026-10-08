class RoomNotFoundError(Exception):
    """Raised when a room cannot be found within the given project."""

    pass


class RoomStillActiveError(Exception):
    """Raised when the requested room is still active (not yet closed)."""

    pass


class MessageCreateError(Exception):
    def __init__(self, error_code: str, error_message, details=None):
        self.error_code = error_code
        self.error_message = error_message
        self.details = details
        super().__init__(error_message)
