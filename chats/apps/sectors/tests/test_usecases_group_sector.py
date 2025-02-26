from rest_framework.test import APITestCase

from chats.apps.accounts.models import User
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.queues.models import Queue
from chats.apps.sectors.models import GroupSector, GroupSectorAuthorization, Sector
from chats.apps.sectors.usecases import (
    AddSectorToGroupSectorUseCase,
    GroupSectorAuthorizationCreationUseCase,
    GroupSectorAuthorizationDeletionUseCase,
    QueueGroupSectorAuthorizationCreationUseCase,
    RemoveSectorFromGroupSectorUseCase,
)


class GroupSectorAuthorizationUseCaseTests(APITestCase):
    fixtures = ["chats/fixtures/fixture_sector.json"]

    def setUp(self):
        self.manager_user = User.objects.get(pk=8)
        self.project = Project.objects.get(pk="34a93b52-231e-11ed-861d-0242ac120002")
        self.sector = Sector.objects.get(pk="21aecf8c-0c73-4059-ba82-4343e0cc627c")
        self.sector_2 = Sector.objects.get(pk="4f88b656-194d-4a83-a166-5d84ba825b8d")

        # Create a test group sector
        self.group_sector = GroupSector.objects.create(
            name="Test Group", project=self.project, rooms_limit=10
        )

        # Create project permission
        self.project_permission = ProjectPermission.objects.get(
            project=self.project, user=self.manager_user, role=1  # 1 = Manager role
        )

        # Create queues
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.queue_2 = Queue.objects.create(name="Test Queue 2", sector=self.sector)

    def test_create_group_sector_authorization_manager(self):
        """Test creating a group sector authorization with manager role"""
        use_case = GroupSectorAuthorizationCreationUseCase(
            group_sector_uuid=self.group_sector.uuid,
            permission_uuid=self.project_permission.uuid,
            role=GroupSectorAuthorization.ROLE_MANAGER,
        )
        use_case.execute()

        # Check if group sector authorization was created
        auth = GroupSectorAuthorization.objects.get(
            group_sector=self.group_sector,
            permission=self.project_permission,
            role=GroupSectorAuthorization.ROLE_MANAGER,
        )
        self.assertIsNotNone(auth)

    def test_create_group_sector_authorization_agent(self):
        """Test creating a group sector authorization with agent role"""
        # Add sector to group first
        self.group_sector.sectors.add(self.sector)

        use_case = GroupSectorAuthorizationCreationUseCase(
            group_sector_uuid=self.group_sector.uuid,
            permission_uuid=self.project_permission.uuid,
            role=GroupSectorAuthorization.ROLE_AGENT,
        )
        use_case.execute()

        # Check if group sector authorization was created
        auth = GroupSectorAuthorization.objects.get(
            group_sector=self.group_sector,
            permission=self.project_permission,
            role=GroupSectorAuthorization.ROLE_AGENT,
        )
        self.assertIsNotNone(auth)

    def test_create_group_sector_authorization_invalid_role(self):
        """Test creating a group sector authorization with invalid role"""
        use_case = GroupSectorAuthorizationCreationUseCase(
            group_sector_uuid=self.group_sector.uuid,
            permission_uuid=self.project_permission.uuid,
            role=3,  # Invalid role
        )
        with self.assertRaises(ValueError) as context:
            use_case.execute()
        self.assertEqual(str(context.exception), "Invalid role")

    def test_delete_group_sector_authorization_manager(self):
        """Test deleting a group sector authorization with manager role"""
        # Create authorization first
        auth = GroupSectorAuthorization.objects.create(
            group_sector=self.group_sector,
            permission=self.project_permission,
            role=GroupSectorAuthorization.ROLE_MANAGER,
        )

        use_case = GroupSectorAuthorizationDeletionUseCase(auth)
        use_case.execute()

        # Check if authorization was deleted
        with self.assertRaises(GroupSectorAuthorization.DoesNotExist):
            GroupSectorAuthorization.objects.get(uuid=auth.uuid)

    def test_add_sector_to_group_sector(self):
        """Test adding a sector to a group sector"""
        use_case = AddSectorToGroupSectorUseCase(
            sector_uuid=self.sector.uuid,
            group_sector=self.group_sector,
        )
        use_case.execute()

        # Check if sector was added to group
        self.assertTrue(
            self.group_sector.sectors.filter(uuid=self.sector.uuid).exists()
        )

    def test_add_sector_to_group_sector_already_exists(self):
        """Test adding a sector that's already in the group sector"""
        # Add sector first
        self.group_sector.sectors.add(self.sector)

        use_case = AddSectorToGroupSectorUseCase(
            sector_uuid=self.sector.uuid,
            group_sector=self.group_sector,
        )
        with self.assertRaises(ValueError) as context:
            use_case.execute()
        self.assertEqual(
            str(context.exception), "Sector is already in another group sector"
        )

    def test_remove_sector_from_group_sector(self):
        """Test removing a sector from a group sector"""
        # Add sector first
        self.group_sector.sectors.add(self.sector)

        use_case = RemoveSectorFromGroupSectorUseCase(
            sector_uuid=self.sector.uuid,
            group_sector=self.group_sector,
        )
        use_case.execute()

        # Check if sector was removed from group
        self.assertFalse(
            self.group_sector.sectors.filter(uuid=self.sector.uuid).exists()
        )

    def test_remove_sector_not_in_group_sector(self):
        """Test removing a sector that's not in the group sector"""
        use_case = RemoveSectorFromGroupSectorUseCase(
            sector_uuid=self.sector.uuid,
            group_sector=self.group_sector,
        )
        with self.assertRaises(ValueError) as context:
            use_case.execute()
        self.assertEqual(str(context.exception), "Sector not found in group sector")

    def test_queue_group_sector_authorization_creation(self):
        """Test creating queue authorizations for a group sector"""
        # Add sector to group
        self.group_sector.sectors.add(self.sector)

        # Create group sector authorization
        GroupSectorAuthorization.objects.create(
            group_sector=self.group_sector,
            permission=self.project_permission,
            role=GroupSectorAuthorization.ROLE_AGENT,
        )

        use_case = QueueGroupSectorAuthorizationCreationUseCase(self.queue)
        use_case.execute()

        # Check if queue authorization was created
        self.assertTrue(
            self.queue.authorizations.filter(
                permission=self.project_permission,
                role=1,
            ).exists()
        )

    def test_create_group_sector_authorization_invalid_group_sector(self):
        """Test creating authorization with invalid group sector UUID"""
        with self.assertRaises(ValueError) as context:
            GroupSectorAuthorizationCreationUseCase(
                group_sector_uuid="00000000-0000-0000-0000-000000000000",  # Invalid UUID
                permission_uuid=self.project_permission.uuid,
                role=GroupSectorAuthorization.ROLE_MANAGER,
            )
        self.assertEqual(str(context.exception), "Group sector or permission not found")

    def test_create_group_sector_authorization_invalid_permission(self):
        """Test creating authorization with invalid permission UUID"""
        with self.assertRaises(ValueError) as context:
            GroupSectorAuthorizationCreationUseCase(
                group_sector_uuid=self.group_sector.uuid,
                permission_uuid="00000000-0000-0000-0000-000000000000",  # Invalid UUID
                role=GroupSectorAuthorization.ROLE_MANAGER,
            )
        self.assertEqual(str(context.exception), "Group sector or permission not found")

    def test_delete_group_sector_authorization_with_sectors(self):
        """Test deleting authorization that has sectors with permissions"""
        # Add sector to group
        self.group_sector.sectors.add(self.sector)

        # Create authorization
        auth = GroupSectorAuthorization.objects.create(
            group_sector=self.group_sector,
            permission=self.project_permission,
            role=GroupSectorAuthorization.ROLE_MANAGER,
        )

        # Create sector authorization
        self.sector.set_user_authorization(self.project_permission, 1)

        use_case = GroupSectorAuthorizationDeletionUseCase(auth)
        use_case.execute()

        # Check if sector authorization was deleted
        self.assertFalse(
            self.sector.authorizations.filter(
                permission=self.project_permission, role=1
            ).exists()
        )

    def test_delete_group_sector_authorization_with_queues(self):
        """Test deleting authorization that has queues with permissions"""
        # Add sector to group
        self.group_sector.sectors.add(self.sector)

        # Create authorization
        auth = GroupSectorAuthorization.objects.create(
            group_sector=self.group_sector,
            permission=self.project_permission,
            role=GroupSectorAuthorization.ROLE_AGENT,
        )

        # Create queue authorization
        self.queue.set_user_authorization(self.project_permission, 1)

        use_case = GroupSectorAuthorizationDeletionUseCase(auth)
        use_case.execute()

        # Check if queue authorization was deleted
        self.assertFalse(
            self.queue.authorizations.filter(
                permission=self.project_permission, role=1
            ).exists()
        )

    def test_delete_group_sector_authorization_error(self):
        """Test error handling when deleting authorization"""
        auth = GroupSectorAuthorization.objects.create(
            group_sector=self.group_sector,
            permission=self.project_permission,
            role=GroupSectorAuthorization.ROLE_MANAGER,
        )

        # Force an error by deleting the authorization before executing use case
        auth.delete()

        use_case = GroupSectorAuthorizationDeletionUseCase(auth)
        with self.assertRaises(ValueError):
            use_case.execute()

    def test_add_sector_to_group_sector_with_manager_permissions(self):
        """Test adding sector creates manager permissions"""
        # Create group sector authorization
        GroupSectorAuthorization.objects.create(
            group_sector=self.group_sector,
            permission=self.project_permission,
            role=GroupSectorAuthorization.ROLE_MANAGER,
        )

        use_case = AddSectorToGroupSectorUseCase(
            sector_uuid=self.sector.uuid,
            group_sector=self.group_sector,
        )
        use_case.execute()

        self.assertTrue(
            self.sector.authorizations.filter(
                permission=self.project_permission, role=1
            ).exists()
        )

    def test_add_sector_to_group_sector_with_queue_permissions(self):
        """Test adding sector creates queue permissions"""
        # Create group sector authorization
        GroupSectorAuthorization.objects.create(
            group_sector=self.group_sector,
            permission=self.project_permission,
            role=GroupSectorAuthorization.ROLE_AGENT,
        )

        use_case = AddSectorToGroupSectorUseCase(
            sector_uuid=self.sector.uuid,
            group_sector=self.group_sector,
        )
        use_case.execute()

        # Check if queue authorization was created
        self.assertTrue(
            self.queue.authorizations.filter(
                permission=self.project_permission, role=1
            ).exists()
        )
