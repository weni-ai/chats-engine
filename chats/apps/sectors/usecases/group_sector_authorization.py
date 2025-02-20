from uuid import UUID

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction

from chats.apps.projects.models import ProjectPermission
from chats.apps.queues.models import Queue
from chats.apps.sectors.models import GroupSector, GroupSectorAuthorization, Sector


class GroupSectorAuthorizationCreationUseCase:
    def __init__(self, group_sector_uuid: UUID, permission_uuid: UUID, role: int):
        try:
            self.group_sector = GroupSector.objects.get(uuid=group_sector_uuid)
            self.permission = ProjectPermission.objects.get(uuid=permission_uuid)
        except Exception as e:
            raise ValueError(str(e))
        self.role = role

    def _create_sector_permissions(self):
        for sector in self.group_sector.sectors.filter(is_deleted=False):
            sector.set_user_authorization(self.permission, 1)

    def _create_queue_permissions(self):
        for sector in self.group_sector.sectors.filter(is_deleted=False):
            for queue in sector.queues.filter(is_deleted=False):
                queue.set_user_authorization(self.permission, 1)

    def _create_group_sector_authorization(self):
        GroupSectorAuthorization.objects.create(
            group_sector=self.group_sector, permission=self.permission, role=self.role
        )

    @transaction.atomic
    def execute(self):
        self._validate_role()
        try:
            if self.role == GroupSectorAuthorization.ROLE_MANAGER:
                self._create_sector_permissions()
            elif self.role == GroupSectorAuthorization.ROLE_AGENT:
                self._create_queue_permissions()
            self._create_group_sector_authorization()
        except Exception as e:
            raise ValueError(str(e))

    def _validate_role(self):
        if self.role not in [
            GroupSectorAuthorization.ROLE_MANAGER,
            GroupSectorAuthorization.ROLE_AGENT,
        ]:
            raise ValueError("Invalid role")


class GroupSectorAuthorizationDeletionUseCase:
    def __init__(self, group_sector_authorization: GroupSectorAuthorization):
        self.group_sector_authorization = group_sector_authorization

    def _delete_sector_permissions(self):
        for sector in self.group_sector_authorization.group_sector.sectors.filter(
            is_deleted=False
        ):
            sector.authorizations.filter(
                permission=self.group_sector_authorization.permission, role=1
            ).delete()

    def _delete_queue_permissions(self):
        for sector in self.group_sector_authorization.group_sector.sectors.filter(
            is_deleted=False
        ):
            for queue in sector.queues.filter(is_deleted=False):
                queue.authorizations.filter(
                    permission=self.group_sector_authorization.permission, role=1
                ).delete()

    def _delete_group_sector_authorization(self):
        self.group_sector_authorization.delete()

    @transaction.atomic
    def execute(self):
        try:
            if (
                self.group_sector_authorization.role
                == GroupSectorAuthorization.ROLE_MANAGER
            ):
                self._delete_sector_permissions()
            elif (
                self.group_sector_authorization.role
                == GroupSectorAuthorization.ROLE_AGENT
            ):
                self._delete_queue_permissions()
            self._delete_group_sector_authorization()
        except Exception as e:
            raise ValueError(str(e))


class QueueGroupSectorAuthorizationCreationUseCase:
    def __init__(self, queue: Queue):
        self.queue = queue

    def _get_group_sectors(self):
        return self.queue.sector.sector_group_sectors.all()

    def _get_agents_authorizations(self):
        for group_sector in self._get_group_sectors():
            authorizations = (
                group_sector.sector_group.group_sector_authorizations.filter(
                    role=GroupSectorAuthorization.ROLE_AGENT
                )
            )
            for authorization in authorizations:
                self.queue.set_user_authorization(authorization.permission, 1)

    @transaction.atomic
    def execute(self):
        self._get_agents_authorizations()


class AddSectorToGroupSectorUseCase:
    def __init__(self, sector_uuid: UUID, group_sector: GroupSector):
        self.sector_uuid = sector_uuid
        self.group_sector = group_sector
        try:
            self.sector = Sector.objects.get(
                uuid=self.sector_uuid, project=self.group_sector.project
            )
        except ObjectDoesNotExist:
            raise ObjectDoesNotExist("Sector not found in project")

    def _add_sector_to_group_sector(self):
        if self.group_sector.sectors.filter(uuid=self.sector_uuid).exists():
            raise ValueError("Sector already in group sector")
        self.group_sector.sectors.add(self.sector)

    def _create_sector_permissions(self):
        for authorization in self.group_sector.group_sector_authorizations.filter(
            role=GroupSectorAuthorization.ROLE_MANAGER
        ):
            self.sector.set_user_authorization(authorization.permission, 1)

    def _create_queue_permissions(self):
        for authorization in self.group_sector.group_sector_authorizations.filter(
            role=GroupSectorAuthorization.ROLE_AGENT
        ):
            for queue in self.sector.queues.filter(is_deleted=False):
                queue.set_user_authorization(authorization.permission, 1)

    @transaction.atomic
    def execute(self):
        self._add_sector_to_group_sector()
        self._create_sector_permissions()
        self._create_queue_permissions()


class RemoveSectorFromGroupSectorUseCase:
    def __init__(self, sector_uuid: UUID, group_sector: GroupSector):
        self.sector_uuid = sector_uuid
        self.group_sector = group_sector

    def _remove_sector_from_group_sector(self):
        if not self.group_sector.sectors.filter(uuid=self.sector_uuid).exists():
            raise ValueError("Sector not found in group sector")
        self.group_sector.sectors.remove(self.sector)

    def _delete_sector_permissions(self):
        for authorization in self.group_sector.group_sector_authorizations.filter(
            role=GroupSectorAuthorization.ROLE_MANAGER
        ):
            self.sector.authorizations.filter(
                permission=authorization.permission, role=1
            ).delete()

    def _delete_queue_permissions(self):
        for authorization in self.group_sector.group_sector_authorizations.filter(
            role=GroupSectorAuthorization.ROLE_AGENT
        ):
            for queue in self.sector.queues.filter(is_deleted=False):
                queue.authorizations.filter(
                    permission=authorization.permission, role=1
                ).delete()

    @transaction.atomic
    def execute(self):
        self._delete_sector_permissions()
        self._delete_queue_permissions()
        self._remove_sector_from_group_sector()
