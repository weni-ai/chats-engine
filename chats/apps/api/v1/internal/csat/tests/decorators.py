import functools

from chats.apps.api.authentication.token import JWTTokenGenerator


def with_project_jwt_token(func):
    """
    Decorator to create a JWT token for the project.

    Usage:
    @with_project_jwt_token
    def test_something(self):
        pass
    """

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        self.jwt_generator = JWTTokenGenerator()
        self.token = self.jwt_generator.generate_token(
            {"project": str(self.project.uuid)}
        )
        return func(self, *args, **kwargs)

    return wrapper


def with_closed_room(func):
    """
    Decorator to create a closed room for the project.
    """

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        self.room.is_active = False
        self.room.save(update_fields=["is_active"])
        return func(self, *args, **kwargs)

    return wrapper
