from chats.apps.projects.models.models import ProjectPermission
from chats.apps.queues.models import QueueAuthorization


def with_queue_authorization(role: int):
    """
    Decorator to create a queue authorization for the user
    in tests. Default role is QueueAuthorization.ROLE_AGENT.

    Usage:
    @with_queue_authorization(role=QueueAuthorization.ROLE_AGENT)
    def test_something(self):
        pass
    """

    def decorator(func):
        def wrapper(self, *args, **kwargs):
            permission = ProjectPermission.objects.filter(
                user=self.user,
                project=self.project,
            ).first()

            if not permission:
                raise ValueError("User does not have a project permission")

            QueueAuthorization.objects.create(
                role=role,
                permission=permission,
                queue=self.queue,
            )
            return func(self, *args, **kwargs)

        return wrapper

    return decorator
