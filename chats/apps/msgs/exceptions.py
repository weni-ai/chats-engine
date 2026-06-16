class RoomNotFoundError(Exception):
    """Raised when a room cannot be found within the given project."""

    pass


class RoomStillActiveError(Exception):
    """Raised when the requested room is still active (not yet closed)."""

    pass
