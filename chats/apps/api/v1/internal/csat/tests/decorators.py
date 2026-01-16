import functools

from chats.apps.api.authentication.token import JWTTokenGenerator


def with_project_jwt_token(func=None, *, room_uuid=None):
    """
    Decorator to create a JWT token for the project in a test.

    Usage:
    @with_project_jwt_token
    def test_something(self):
        pass

    Or with a specific room_uuid:
    @with_project_jwt_token(room_uuid="some-uuid")
    def test_something(self):
        pass
    """
    if func is None:

        def decorator(f):
            return with_project_jwt_token(f, room_uuid=room_uuid)

        return decorator

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        self.jwt_generator = JWTTokenGenerator()
        room = room_uuid if room_uuid is not None else str(self.room.uuid)
        self.token = self.jwt_generator.generate_token(
            {"project": str(self.project.uuid), "room": room}
        )
        return func(self, *args, **kwargs)

    return wrapper


def with_closed_room(func):
    """
    Decorator to close a room in a test.
    """

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        self.room.is_active = False
        self.room.save(update_fields=["is_active"])
        return func(self, *args, **kwargs)

    return wrapper
