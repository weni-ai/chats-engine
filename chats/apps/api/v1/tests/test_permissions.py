from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ObjectDoesNotExist
from django.test import SimpleTestCase, TestCase
from rest_framework.exceptions import ValidationError

from chats.apps.api.v1.permissions import (
    AnyQueueAgentPermission,
    AnySectorManagerPermission,
    DeleteQueuePermission,
    HasAgentPermissionAnyQueueSector,
    HasDashboardAccess,
    HasObjectProjectPermission,
    IsProjectAdmin,
    IsQueueAgent,
    IsSectorAgent,
    IsSectorManager,
    ProjectAccessPermission,
    ProjectAnyPermission,
    ProjectBodyPermission,
    ProjectExternalPermission,
    ProjectQueryParamPermission,
    QueueAddAgentPermission,
    SectorAddQueuePermission,
    SectorAgentReadOnlyListPermission,
    SectorAgentReadOnlyRetrievePermission,
    SectorAnyPermission,
)
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.rooms.models import Room


def _request(user=None, data=None, query_params=None, method="GET"):
    return SimpleNamespace(
        user=user or Mock(),
        data=data or {},
        query_params=query_params or {},
        method=method,
        is_anonymous=(
            getattr(user, "is_anonymous", False) if user is not None else False
        ),
    )


def _view(action="list"):
    return SimpleNamespace(action=action)


class IsProjectAdminTests(SimpleTestCase):
    @patch("chats.apps.api.v1.permissions.GetPermission")
    def test_has_permission_list_admin(self, mock_get_perm):
        mock_get_perm.return_value.permission = SimpleNamespace(is_admin=True)
        self.assertTrue(
            IsProjectAdmin().has_permission(
                _request(data={"project": "p"}), _view("list")
            )
        )

    @patch("chats.apps.api.v1.permissions.GetPermission")
    def test_has_permission_create_not_admin(self, mock_get_perm):
        mock_get_perm.return_value.permission = SimpleNamespace(is_admin=False)
        self.assertFalse(
            IsProjectAdmin().has_permission(
                _request(data={"project": "p"}), _view("create")
            )
        )

    def test_has_permission_other_action_delegates(self):
        self.assertTrue(IsProjectAdmin().has_permission(_request(), _view("retrieve")))

    def test_has_object_permission_anonymous(self):
        self.assertFalse(
            IsProjectAdmin().has_object_permission(
                _request(user=AnonymousUser()), _view(), Mock()
            )
        )

    def test_has_object_permission_admin(self):
        obj = Mock()
        obj.get_permission.return_value = SimpleNamespace(is_admin=True)
        self.assertTrue(
            IsProjectAdmin().has_object_permission(_request(user=Mock()), _view(), obj)
        )

    def test_has_object_permission_missing(self):
        obj = Mock()
        obj.get_permission.side_effect = ProjectPermission.DoesNotExist
        self.assertFalse(
            IsProjectAdmin().has_object_permission(_request(user=Mock()), _view(), obj)
        )


class IsSectorManagerTests(SimpleTestCase):
    @patch("chats.apps.api.v1.permissions.GetPermission")
    def test_has_permission_list_manager(self, mock_get_perm):
        perm = Mock()
        perm.is_manager.return_value = True
        mock_get_perm.return_value.permission = perm
        self.assertTrue(
            IsSectorManager().has_permission(
                _request(data={"sector": "s1"}), _view("list")
            )
        )
        perm.is_manager.assert_called_once_with(sector="s1", queue=None)

    @patch("chats.apps.api.v1.permissions.GetPermission")
    def test_has_permission_none_permission(self, mock_get_perm):
        mock_get_perm.return_value.permission = None
        self.assertFalse(
            IsSectorManager().has_permission(
                _request(data={"sector": "s1"}), _view("create")
            )
        )

    def test_has_permission_other_action(self):
        self.assertTrue(IsSectorManager().has_permission(_request(), _view("retrieve")))

    def test_has_object_permission_anonymous(self):
        self.assertFalse(
            IsSectorManager().has_object_permission(
                _request(user=AnonymousUser()), _view(), Mock()
            )
        )

    def test_has_object_permission_manager(self):
        obj = Mock()
        obj.sector.pk = "sec-1"
        perm = Mock()
        perm.is_manager.return_value = True
        obj.get_permission.return_value = perm
        self.assertTrue(
            IsSectorManager().has_object_permission(_request(user=Mock()), _view(), obj)
        )
        perm.is_manager.assert_called_once_with(sector="sec-1")

    def test_has_object_permission_missing(self):
        obj = Mock()
        obj.get_permission.side_effect = ProjectPermission.DoesNotExist
        self.assertFalse(
            IsSectorManager().has_object_permission(_request(user=Mock()), _view(), obj)
        )


class IsSectorAgentTests(SimpleTestCase):
    @patch("chats.apps.api.v1.permissions.GetPermission")
    def test_has_permission_list(self, mock_get_perm):
        perm = Mock()
        perm.is_agent.return_value = True
        mock_get_perm.return_value.permission = perm
        self.assertTrue(
            IsSectorAgent().has_permission(
                _request(data={"sector": "s", "queue": "q"}), _view("list")
            )
        )

    def test_has_permission_other_action(self):
        self.assertTrue(IsSectorAgent().has_permission(_request(), _view("update")))

    def test_has_object_permission_anonymous(self):
        self.assertFalse(
            IsSectorAgent().has_object_permission(
                _request(user=AnonymousUser()), _view(), Mock()
            )
        )

    def test_has_object_permission_agent(self):
        obj = Mock()
        obj.sector.pk = "sec"
        perm = Mock()
        perm.is_agent.return_value = True
        obj.get_permission.return_value = perm
        self.assertTrue(
            IsSectorAgent().has_object_permission(_request(user=Mock()), _view(), obj)
        )

    def test_has_object_permission_missing(self):
        obj = Mock()
        obj.get_permission.side_effect = ProjectPermission.DoesNotExist
        self.assertFalse(
            IsSectorAgent().has_object_permission(_request(user=Mock()), _view(), obj)
        )


class ProjectAnyPermissionTests(SimpleTestCase):
    def test_exists_true(self):
        obj = Mock()
        obj.permissions.filter.return_value.exists.return_value = True
        self.assertTrue(
            ProjectAnyPermission().has_object_permission(
                _request(user=Mock()), _view(), obj
            )
        )

    def test_fallback_get_permission(self):
        obj = Mock()
        obj.permissions.filter.side_effect = Exception("no perms")
        obj.get_permission.return_value = True
        self.assertTrue(
            ProjectAnyPermission().has_object_permission(
                _request(user=Mock()), _view(), obj
            )
        )


class HasObjectProjectPermissionTests(SimpleTestCase):
    def test_no_project(self):
        obj = SimpleNamespace(project=None)
        self.assertFalse(
            HasObjectProjectPermission().has_object_permission(
                _request(user=Mock()), _view(), obj
            )
        )

    @patch("chats.apps.api.v1.permissions.ProjectPermission.objects")
    def test_with_project(self, mock_objects):
        mock_objects.filter.return_value.exists.return_value = True
        obj = SimpleNamespace(project=Mock())
        self.assertTrue(
            HasObjectProjectPermission().has_object_permission(
                _request(user=Mock()), _view(), obj
            )
        )


class AnyQueueAgentPermissionTests(SimpleTestCase):
    @patch("chats.apps.api.v1.permissions.GetPermission")
    def test_is_agent(self, mock_get_perm):
        perm = Mock()
        perm.is_agent.return_value = True
        mock_get_perm.return_value.permission = perm
        self.assertTrue(AnyQueueAgentPermission().has_permission(_request(), _view()))

    @patch("chats.apps.api.v1.permissions.GetPermission")
    def test_attribute_error(self, mock_get_perm):
        mock_get_perm.return_value.permission = None
        self.assertFalse(AnyQueueAgentPermission().has_permission(_request(), _view()))


class AnySectorManagerPermissionTests(SimpleTestCase):
    @patch("chats.apps.api.v1.permissions.GetPermission")
    def test_is_manager(self, mock_get_perm):
        perm = Mock()
        perm.is_manager.return_value = True
        mock_get_perm.return_value.permission = perm
        self.assertTrue(
            AnySectorManagerPermission().has_permission(_request(), _view())
        )

    @patch("chats.apps.api.v1.permissions.GetPermission")
    def test_attribute_error(self, mock_get_perm):
        mock_get_perm.return_value.permission = None
        self.assertFalse(
            AnySectorManagerPermission().has_permission(_request(), _view())
        )


class ProjectAccessPermissionTests(SimpleTestCase):
    def test_missing_project_raises(self):
        with self.assertRaises(ValidationError):
            ProjectAccessPermission().has_permission(_request(), _view())

    @patch("chats.apps.api.v1.permissions.GetPermission")
    def test_permission_none(self, mock_get_perm):
        mock_get_perm.return_value.permission = None
        self.assertFalse(
            ProjectAccessPermission().has_permission(
                _request(data={"project": "p"}), _view()
            )
        )

    @patch("chats.apps.api.v1.permissions.GetPermission")
    def test_permission_ok_caches(self, mock_get_perm):
        perm = Mock()
        mock_get_perm.return_value.permission = perm
        request = _request(data={"project": "p"})
        self.assertTrue(ProjectAccessPermission().has_permission(request, _view()))
        self.assertIs(request._cached_project_permission, perm)

    @patch("chats.apps.api.v1.permissions.GetPermission")
    def test_does_not_exist(self, mock_get_perm):
        mock_get_perm.side_effect = ProjectPermission.DoesNotExist
        self.assertFalse(
            ProjectAccessPermission().has_permission(
                _request(data={"project": "p"}), _view()
            )
        )


class IsQueueAgentTests(SimpleTestCase):
    @patch("chats.apps.api.v1.permissions.GetPermission")
    def test_has_permission_with_queue(self, mock_get_perm):
        perm = Mock()
        perm.is_agent.return_value = True
        mock_get_perm.return_value.permission = perm
        self.assertTrue(
            IsQueueAgent().has_permission(_request(data={"queue": "q1"}), _view("list"))
        )
        perm.is_agent.assert_called_once_with("q1")

    @patch("chats.apps.api.v1.permissions.GetPermission")
    def test_has_permission_with_sector(self, mock_get_perm):
        perm = Mock()
        perm.is_manager.return_value = True
        mock_get_perm.return_value.permission = perm
        self.assertTrue(
            IsQueueAgent().has_permission(
                _request(data={"sector": "s1"}), _view("create")
            )
        )

    def test_has_permission_other_action(self):
        self.assertTrue(IsQueueAgent().has_permission(_request(), _view("retrieve")))

    def test_has_object_permission_anonymous(self):
        self.assertFalse(
            IsQueueAgent().has_object_permission(
                _request(user=AnonymousUser()), _view(), Mock()
            )
        )

    def test_has_object_permission_room_owner(self):
        user = Mock()
        room = Mock(spec=Room)
        room.user = user
        self.assertTrue(
            IsQueueAgent().has_object_permission(_request(user=user), _view(), room)
        )

    def test_has_object_permission_missing(self):
        obj = Mock()
        obj.get_permission.side_effect = ProjectPermission.DoesNotExist
        self.assertFalse(
            IsQueueAgent().has_object_permission(_request(user=Mock()), _view(), obj)
        )

    def test_has_object_permission_falsy_perm(self):
        obj = Mock()
        obj.get_permission.return_value = None
        self.assertFalse(
            IsQueueAgent().has_object_permission(_request(user=Mock()), _view(), obj)
        )

    def test_has_object_permission_agent(self):
        obj = Mock()
        obj.queue.pk = "q1"
        perm = Mock()
        perm.is_agent.return_value = True
        obj.get_permission.return_value = perm
        self.assertTrue(
            IsQueueAgent().has_object_permission(_request(user=Mock()), _view(), obj)
        )

    def test_has_object_permission_object_does_not_exist_fallback(self):
        obj = Mock()
        obj.queue.pk = "q1"
        perm = Mock()
        perm.is_agent.side_effect = ObjectDoesNotExist
        perm.is_manager.return_value = True
        obj.get_permission.return_value = perm
        self.assertTrue(
            IsQueueAgent().has_object_permission(_request(user=Mock()), _view(), obj)
        )


class SectorAnyPermissionTests(SimpleTestCase):
    def test_anonymous(self):
        self.assertFalse(
            SectorAnyPermission().has_object_permission(
                _request(user=AnonymousUser()), _view(), Mock()
            )
        )

    def test_authorized(self):
        obj = Mock()
        obj.get_permission.return_value = SimpleNamespace(is_authorized=True)
        self.assertTrue(
            SectorAnyPermission().has_object_permission(
                _request(user=Mock()), _view(), obj
            )
        )

    def test_missing(self):
        from chats.apps.sectors.models import SectorAuthorization

        obj = Mock()
        obj.get_permission.side_effect = SectorAuthorization.DoesNotExist
        self.assertFalse(
            SectorAnyPermission().has_object_permission(
                _request(user=Mock()), _view(), obj
            )
        )


class ProjectExternalPermissionTests(SimpleTestCase):
    @patch("chats.apps.api.v1.permissions.GetPermission")
    def test_has_permission_list(self, mock_get_perm):
        mock_get_perm.return_value.permission = SimpleNamespace(is_admin=True)
        self.assertTrue(
            ProjectExternalPermission().has_permission(_request(), _view("list"))
        )

    def test_has_permission_other(self):
        self.assertTrue(
            ProjectExternalPermission().has_permission(_request(), _view("retrieve"))
        )

    def test_has_object_anonymous(self):
        self.assertFalse(
            ProjectExternalPermission().has_object_permission(
                _request(user=AnonymousUser()), _view(), Mock()
            )
        )

    def test_has_object_admin(self):
        obj = Mock()
        obj.get_permission.return_value = SimpleNamespace(is_admin=True)
        self.assertTrue(
            ProjectExternalPermission().has_object_permission(
                _request(user=Mock()), _view(), obj
            )
        )

    def test_has_object_missing(self):
        obj = Mock()
        obj.get_permission.side_effect = ProjectPermission.DoesNotExist
        self.assertFalse(
            ProjectExternalPermission().has_object_permission(
                _request(user=Mock()), _view(), obj
            )
        )


class SectorAgentReadOnlyListPermissionTests(SimpleTestCase):
    def test_anonymous(self):
        self.assertFalse(
            SectorAgentReadOnlyListPermission().has_permission(
                _request(user=AnonymousUser()), _view()
            )
        )

    @patch("chats.apps.api.v1.permissions.Queue.objects")
    def test_with_queue(self, mock_queue_objects):
        queue = Mock()
        queue.get_permission.return_value = True
        mock_queue_objects.filter.return_value.first.return_value = queue
        self.assertTrue(
            SectorAgentReadOnlyListPermission().has_permission(
                _request(user=Mock(), query_params={"sector": "s"}), _view()
            )
        )

    @patch("chats.apps.api.v1.permissions.Queue.objects")
    def test_queue_does_not_exist(self, mock_queue_objects):
        from chats.apps.queues.models import Queue

        mock_queue_objects.filter.side_effect = Queue.DoesNotExist
        self.assertFalse(
            SectorAgentReadOnlyListPermission().has_permission(
                _request(user=Mock(), query_params={"sector": "s"}), _view()
            )
        )


class SectorAgentReadOnlyRetrievePermissionTests(SimpleTestCase):
    def test_anonymous(self):
        self.assertFalse(
            SectorAgentReadOnlyRetrievePermission().has_object_permission(
                _request(user=AnonymousUser()), _view(), Mock()
            )
        )

    def test_authorized(self):
        obj = Mock()
        obj.get_permission.return_value = True
        self.assertTrue(
            SectorAgentReadOnlyRetrievePermission().has_object_permission(
                _request(user=Mock()), _view(), obj
            )
        )

    def test_missing(self):
        from chats.apps.queues.models import QueueAuthorization

        obj = Mock()
        obj.get_permission.side_effect = QueueAuthorization.DoesNotExist
        self.assertFalse(
            SectorAgentReadOnlyRetrievePermission().has_object_permission(
                _request(user=Mock()), _view(), obj
            )
        )


class SectorAddQueuePermissionTests(SimpleTestCase):
    def test_anonymous(self):
        self.assertFalse(
            SectorAddQueuePermission().has_permission(
                _request(user=AnonymousUser()), _view()
            )
        )

    @patch("chats.apps.api.v1.permissions.Queue.objects")
    def test_authorized(self, mock_queue_objects):
        queue = Mock()
        queue.get_permission.return_value = True
        mock_queue_objects.filter.return_value.first.return_value = queue
        self.assertTrue(
            SectorAddQueuePermission().has_permission(
                _request(user=Mock(), data={"sector": "s"}), _view()
            )
        )

    @patch("chats.apps.api.v1.permissions.Queue.objects")
    def test_queue_does_not_exist(self, mock_queue_objects):
        from chats.apps.queues.models import Queue

        mock_queue_objects.filter.side_effect = Queue.DoesNotExist
        self.assertFalse(
            SectorAddQueuePermission().has_permission(
                _request(user=Mock(), data={"sector": "s"}), _view()
            )
        )


class DeleteQueuePermissionTests(SimpleTestCase):
    def test_anonymous(self):
        self.assertFalse(
            DeleteQueuePermission().has_object_permission(
                _request(user=AnonymousUser()), _view(), Mock()
            )
        )

    def test_authorized(self):
        obj = Mock()
        obj.get_permission.return_value = True
        self.assertTrue(
            DeleteQueuePermission().has_object_permission(
                _request(user=Mock()), _view(), obj
            )
        )

    def test_missing(self):
        from chats.apps.queues.models import Queue

        obj = Mock()
        obj.get_permission.side_effect = Queue.DoesNotExist
        self.assertFalse(
            DeleteQueuePermission().has_object_permission(
                _request(user=Mock()), _view(), obj
            )
        )


class QueueAddAgentPermissionTests(SimpleTestCase):
    def test_anonymous(self):
        self.assertFalse(
            QueueAddAgentPermission().has_permission(
                _request(user=AnonymousUser()), _view()
            )
        )

    @patch("chats.apps.api.v1.permissions.SectorAuthorization.objects")
    def test_no_sector_auth(self, mock_objects):
        mock_objects.filter.return_value.first.return_value = None
        self.assertFalse(
            QueueAddAgentPermission().has_permission(_request(user=Mock()), _view())
        )

    @patch("chats.apps.api.v1.permissions.SectorAuthorization.objects")
    def test_authorized(self, mock_objects):
        auth = Mock()
        auth.get_permission.return_value = True
        mock_objects.filter.return_value.first.return_value = auth
        self.assertTrue(
            QueueAddAgentPermission().has_permission(_request(user=Mock()), _view())
        )

    @patch("chats.apps.api.v1.permissions.SectorAuthorization.objects")
    def test_queue_does_not_exist(self, mock_objects):
        from chats.apps.queues.models import Queue

        mock_objects.filter.side_effect = Queue.DoesNotExist
        self.assertFalse(
            QueueAddAgentPermission().has_permission(_request(user=Mock()), _view())
        )


class HasAgentPermissionAnyQueueSectorTests(SimpleTestCase):
    def test_manager(self):
        user = Mock()
        obj = Mock()
        admin = Mock()
        admin.is_manager.return_value = True
        obj.project.get_permission.return_value = admin
        self.assertTrue(
            HasAgentPermissionAnyQueueSector().has_object_permission(
                _request(user=user), _view(), obj
            )
        )

    def test_queue_agent(self):
        user = Mock()
        obj = Mock()
        obj.project.get_permission.return_value = None
        obj.queue_agents = [user]
        self.assertTrue(
            HasAgentPermissionAnyQueueSector().has_object_permission(
                _request(user=user), _view(), obj
            )
        )

    def test_denied(self):
        user = Mock()
        obj = Mock()
        obj.project.get_permission.return_value = None
        obj.queue_agents = []
        self.assertFalse(
            HasAgentPermissionAnyQueueSector().has_object_permission(
                _request(user=user), _view(), obj
            )
        )


class HasDashboardAccessTests(SimpleTestCase):
    def test_anonymous(self):
        self.assertFalse(
            HasDashboardAccess().has_object_permission(
                _request(user=AnonymousUser()), _view(), Mock()
            )
        )

    def test_admin_role(self):
        obj = Mock()
        perm = Mock(role=1)
        perm.sector_authorizations.exists.return_value = False
        obj.permissions.get.return_value = perm
        self.assertTrue(
            HasDashboardAccess().has_object_permission(
                _request(user=Mock()), _view(), obj
            )
        )

    def test_sector_auth(self):
        obj = Mock()
        perm = Mock(role=0)
        perm.sector_authorizations.exists.return_value = True
        obj.permissions.get.return_value = perm
        self.assertTrue(
            HasDashboardAccess().has_object_permission(
                _request(user=Mock()), _view(), obj
            )
        )

    def test_no_access(self):
        obj = Mock()
        perm = Mock(role=0)
        perm.sector_authorizations.exists.return_value = False
        obj.permissions.get.return_value = perm
        self.assertFalse(
            HasDashboardAccess().has_object_permission(
                _request(user=Mock()), _view(), obj
            )
        )

    def test_missing(self):
        obj = Mock()
        obj.permissions.get.side_effect = ProjectPermission.DoesNotExist
        self.assertFalse(
            HasDashboardAccess().has_object_permission(
                _request(user=Mock()), _view(), obj
            )
        )


class ProjectQueryParamPermissionDBTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        self.user = User.objects.create_user(email="qp@example.com", password="x")
        self.project = Project.objects.create(name="P")
        ProjectPermission.objects.create(
            project=self.project, user=self.user, role=ProjectPermission.ROLE_ADMIN
        )

    def test_anonymous(self):
        user = AnonymousUser()
        request = _request(
            user=user, query_params={"project_uuid": str(self.project.uuid)}
        )
        request.is_anonymous = True
        self.assertFalse(ProjectQueryParamPermission().has_permission(request, _view()))

    def test_missing_uuid_raises(self):
        request = _request(user=self.user, query_params={})
        request.is_anonymous = False
        with self.assertRaises(ValidationError):
            ProjectQueryParamPermission().has_permission(request, _view())

    def test_with_permission(self):
        request = _request(
            user=self.user, query_params={"project_uuid": str(self.project.uuid)}
        )
        request.is_anonymous = False
        self.assertTrue(ProjectQueryParamPermission().has_permission(request, _view()))

    def test_without_permission(self):
        import uuid

        request = _request(
            user=self.user, query_params={"project_uuid": str(uuid.uuid4())}
        )
        request.is_anonymous = False
        self.assertFalse(ProjectQueryParamPermission().has_permission(request, _view()))


class ProjectBodyPermissionDBTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        self.user = User.objects.create_user(email="body@example.com", password="x")
        self.project = Project.objects.create(name="P")
        ProjectPermission.objects.create(
            project=self.project, user=self.user, role=ProjectPermission.ROLE_ATTENDANT
        )

    def test_anonymous(self):
        request = _request(
            user=AnonymousUser(), data={"project_uuid": str(self.project.uuid)}
        )
        request.is_anonymous = True
        self.assertFalse(ProjectBodyPermission().has_permission(request, _view()))

    def test_missing_raises(self):
        request = _request(user=self.user, data={})
        request.is_anonymous = False
        with self.assertRaises(ValidationError):
            ProjectBodyPermission().has_permission(request, _view())

    def test_with_permission(self):
        request = _request(
            user=self.user, data={"project_uuid": str(self.project.uuid)}
        )
        request.is_anonymous = False
        self.assertTrue(ProjectBodyPermission().has_permission(request, _view()))
