from functools import wraps


def with_room_user(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        assert hasattr(self, "room"), "Room must be set"
        assert hasattr(self, "user"), "User must be set"

        self.room.user = self.user
        self.room.save()

        return func(self, *args, **kwargs)

    return wrapper
