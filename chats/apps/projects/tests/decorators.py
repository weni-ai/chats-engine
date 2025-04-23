import functools

from chats.apps.projects.models.models import ProjectPermission


def with_project_permission(role=ProjectPermission.ROLE_ADMIN):
    """
    Decorator to create a project permission for the user
    in tests. Default role is ProjectPermission.ROLE_ADMIN.

    Usage:
    @with_project_permission(role=ProjectPermission.ROLE_ADMIN)
    def test_something(self):
        pass
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            ProjectPermission.objects.create(
                project=self.project,
                user=self.user,
                role=role,
            )

            return func(self, *args, **kwargs)

        return wrapper

    return decorator
