import functools
from chats.apps.projects.models.models import ProjectPermission
from chats.apps.sectors.models import SectorAuthorization


def with_sector_authorization(role=SectorAuthorization.ROLE_MANAGER):
    """
    Decorator to create a sector authorization for the user
    in tests. Default role is SectorAuthorization.ROLE_MANAGER.

    Usage:
    @with_sector_authorization(role=SectorAuthorization.ROLE_MANAGER)
    def test_something(self):
        pass
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            permission = ProjectPermission.objects.filter(
                user=self.user,
                project=self.project,
            ).first()

            if not permission:
                raise ValueError("User does not have a project permission")

            SectorAuthorization.objects.create(
                permission=permission,
                sector=self.sector,
                role=role,
            )
            return func(self, *args, **kwargs)

        return wrapper

    return decorator
