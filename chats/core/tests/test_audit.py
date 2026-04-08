from django.test import RequestFactory, TestCase

from chats.apps.accounts.models import User
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.sectors.models import Sector, SectorAuthorization, SectorHoliday
from chats.apps.quickmessages.models import QuickMessage
from chats.apps.projects.models import DeletionLog
from chats.core.middleware import CurrentUserMiddleware, _thread_locals, get_current_user


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _set_current_user(user):
    _thread_locals.user = user


def _clear_current_user():
    _thread_locals.user = None


# ---------------------------------------------------------------------------
# CurrentUserMiddleware
# ---------------------------------------------------------------------------

class CurrentUserMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(email="middleware@test.com", password="x")

    def test_user_is_available_via_get_current_user_during_request(self):
        captured = {}

        def get_response(request):
            captured["user"] = get_current_user()
            from django.http import HttpResponse
            return HttpResponse()

        middleware = CurrentUserMiddleware(get_response)
        request = self.factory.get("/")
        request.user = self.user
        middleware(request)

        self.assertEqual(captured["user"], self.user)

    def test_user_is_cleared_after_request_completes(self):
        def get_response(request):
            from django.http import HttpResponse
            return HttpResponse()

        middleware = CurrentUserMiddleware(get_response)
        request = self.factory.get("/")
        request.user = self.user
        middleware(request)

        self.assertIsNone(get_current_user())

    def test_user_is_cleared_even_when_view_raises_exception(self):
        def get_response(request):
            raise ValueError("view exploded")

        middleware = CurrentUserMiddleware(get_response)
        request = self.factory.get("/")
        request.user = self.user

        with self.assertRaises(ValueError):
            middleware(request)

        self.assertIsNone(get_current_user())


# ---------------------------------------------------------------------------
# AuditableMixin — created_by / modified_by
# ---------------------------------------------------------------------------

class AuditableMixinCreateUpdateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="audit@test.com", password="x")
        self.other_user = User.objects.create_user(email="other@test.com", password="x")
        self.project = Project.objects.create(name="Audit Project", timezone="UTC")

    def tearDown(self):
        _clear_current_user()

    def _make_sector(self, name="Sector Audit"):
        return Sector.objects.create(
            name=name,
            project=self.project,
            rooms_limit=5,
            work_start="08:00",
            work_end="18:00",
        )

    def test_created_by_is_set_on_creation(self):
        _set_current_user(self.user)
        sector = self._make_sector()

        self.assertEqual(sector.created_by, self.user)

    def test_modified_by_is_set_on_creation(self):
        _set_current_user(self.user)
        sector = self._make_sector()

        self.assertEqual(sector.modified_by, self.user)

    def test_modified_by_is_updated_on_save(self):
        _set_current_user(self.user)
        sector = self._make_sector()

        _set_current_user(self.other_user)
        sector.rooms_limit = 10
        sector.save()

        sector.refresh_from_db()
        self.assertEqual(sector.modified_by, self.other_user)

    def test_created_by_is_not_overwritten_on_update(self):
        _set_current_user(self.user)
        sector = self._make_sector()

        _set_current_user(self.other_user)
        sector.rooms_limit = 10
        sector.save()

        sector.refresh_from_db()
        self.assertEqual(sector.created_by, self.user)

    def test_fields_are_null_when_no_user_in_middleware(self):
        _clear_current_user()
        sector = self._make_sector("No User Sector")

        self.assertIsNone(sector.created_by)
        self.assertIsNone(sector.modified_by)

    def test_fields_are_null_for_anonymous_user(self):
        from django.contrib.auth.models import AnonymousUser
        _set_current_user(AnonymousUser())
        sector = self._make_sector("Anon Sector")

        self.assertIsNone(sector.created_by)
        self.assertIsNone(sector.modified_by)


# ---------------------------------------------------------------------------
# AuditableMixin — deleted_by (soft delete)
# ---------------------------------------------------------------------------

class AuditableMixinSoftDeleteTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="deleter@test.com", password="x")
        self.project = Project.objects.create(name="Delete Project", timezone="UTC")
        self.sector = Sector.objects.create(
            name="Sector To Delete",
            project=self.project,
            rooms_limit=5,
            work_start="08:00",
            work_end="18:00",
        )

    def tearDown(self):
        _clear_current_user()

    def test_deleted_by_is_set_on_soft_delete(self):
        _set_current_user(self.user)
        self.sector.is_deleted = True
        self.sector.save()

        self.sector.refresh_from_db()
        self.assertEqual(self.sector.deleted_by, self.user)

    def test_deleted_by_is_not_set_when_is_deleted_is_false(self):
        _set_current_user(self.user)
        self.sector.rooms_limit = 10
        self.sector.save()

        self.sector.refresh_from_db()
        self.assertIsNone(self.sector.deleted_by)

    def test_deleted_by_is_null_when_no_user_in_middleware(self):
        _clear_current_user()
        self.sector.is_deleted = True
        self.sector.save()

        self.sector.refresh_from_db()
        self.assertIsNone(self.sector.deleted_by)

    def test_deleted_by_is_not_overwritten_if_already_set(self):
        first_user = User.objects.create_user(email="first@test.com", password="x")
        second_user = User.objects.create_user(email="second@test.com", password="x")

        _set_current_user(first_user)
        self.sector.is_deleted = True
        self.sector.save()

        _set_current_user(second_user)
        self.sector.save()

        self.sector.refresh_from_db()
        self.assertEqual(self.sector.deleted_by, first_user)

    def test_deleted_by_is_set_via_sector_holiday_soft_delete(self):
        """Covers the SectorHoliday.delete() override path."""
        import datetime
        holiday = SectorHoliday.objects.create(
            sector=self.sector,
            date=datetime.date(2025, 12, 25),
            day_type=SectorHoliday.CLOSED,
        )
        _set_current_user(self.user)
        holiday.delete()

        holiday.refresh_from_db()
        self.assertEqual(holiday.deleted_by, self.user)


# ---------------------------------------------------------------------------
# DeletionLog — QueueAuthorization
# ---------------------------------------------------------------------------

class QueueAuthorizationDeletionLogTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="manager@test.com", password="x")
        self.agent = User.objects.create_user(email="agent@test.com", password="x")
        self.project = Project.objects.create(name="Log Project", timezone="UTC")
        self.permission = ProjectPermission.objects.create(
            project=self.project,
            user=self.agent,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        self.sector = Sector.objects.create(
            name="Log Sector",
            project=self.project,
            rooms_limit=5,
            work_start="08:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Log Queue", sector=self.sector)
        self.queue_auth = QueueAuthorization.objects.create(
            permission=self.permission,
            queue=self.queue,
            role=QueueAuthorization.ROLE_AGENT,
        )

    def tearDown(self):
        _clear_current_user()

    def test_deletion_log_is_created_on_hard_delete(self):
        _set_current_user(self.user)
        self.queue_auth.delete()

        self.assertEqual(DeletionLog.objects.filter(model_name="QueueAuthorization").count(), 1)

    def test_deletion_log_records_correct_deleted_by(self):
        _set_current_user(self.user)
        self.queue_auth.delete()

        log = DeletionLog.objects.get(model_name="QueueAuthorization")
        self.assertEqual(log.deleted_by, self.user)

    def test_deletion_log_records_correct_project(self):
        _set_current_user(self.user)
        self.queue_auth.delete()

        log = DeletionLog.objects.get(model_name="QueueAuthorization")
        self.assertEqual(log.project, self.project)

    def test_deletion_log_object_repr_contains_queue_and_agent(self):
        _set_current_user(self.user)
        self.queue_auth.delete()

        log = DeletionLog.objects.get(model_name="QueueAuthorization")
        self.assertIn(self.queue.name, log.object_repr)
        self.assertIn(self.agent.email, log.object_repr)

    def test_deletion_log_deleted_by_is_null_when_no_user(self):
        _clear_current_user()
        self.queue_auth.delete()

        log = DeletionLog.objects.get(model_name="QueueAuthorization")
        self.assertIsNone(log.deleted_by)


# ---------------------------------------------------------------------------
# DeletionLog — SectorAuthorization
# ---------------------------------------------------------------------------

class SectorAuthorizationDeletionLogTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="admin@test.com", password="x")
        self.manager = User.objects.create_user(email="manager@test.com", password="x")
        self.project = Project.objects.create(name="SA Log Project", timezone="UTC")
        self.permission = ProjectPermission.objects.create(
            project=self.project,
            user=self.manager,
            role=ProjectPermission.ROLE_ADMIN,
        )
        self.sector = Sector.objects.create(
            name="SA Log Sector",
            project=self.project,
            rooms_limit=5,
            work_start="08:00",
            work_end="18:00",
        )
        self.sector_auth = SectorAuthorization.objects.create(
            permission=self.permission,
            sector=self.sector,
            role=SectorAuthorization.ROLE_MANAGER,
        )

    def tearDown(self):
        _clear_current_user()

    def test_deletion_log_is_created_on_hard_delete(self):
        _set_current_user(self.user)
        self.sector_auth.delete()

        self.assertEqual(DeletionLog.objects.filter(model_name="SectorAuthorization").count(), 1)

    def test_deletion_log_records_correct_deleted_by(self):
        _set_current_user(self.user)
        self.sector_auth.delete()

        log = DeletionLog.objects.get(model_name="SectorAuthorization")
        self.assertEqual(log.deleted_by, self.user)

    def test_deletion_log_object_repr_contains_sector_and_manager(self):
        _set_current_user(self.user)
        self.sector_auth.delete()

        log = DeletionLog.objects.get(model_name="SectorAuthorization")
        self.assertIn(self.sector.name, log.object_repr)
        self.assertIn(self.manager.email, log.object_repr)


# ---------------------------------------------------------------------------
# DeletionLog — QuickMessage
# ---------------------------------------------------------------------------

class QuickMessageDeletionLogTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="qm@test.com", password="x")
        self.project = Project.objects.create(name="QM Log Project", timezone="UTC")
        self.sector = Sector.objects.create(
            name="QM Sector",
            project=self.project,
            rooms_limit=5,
            work_start="08:00",
            work_end="18:00",
        )
        self.quick_message = QuickMessage.objects.create(
            user=self.user,
            shortcut="/oi",
            text="Olá, como posso ajudar?",
            sector=self.sector,
        )

    def tearDown(self):
        _clear_current_user()

    def test_deletion_log_is_created_on_hard_delete(self):
        _set_current_user(self.user)
        self.quick_message.delete()

        self.assertEqual(DeletionLog.objects.filter(model_name="QuickMessage").count(), 1)

    def test_deletion_log_records_correct_deleted_by(self):
        _set_current_user(self.user)
        self.quick_message.delete()

        log = DeletionLog.objects.get(model_name="QuickMessage")
        self.assertEqual(log.deleted_by, self.user)

    def test_deletion_log_object_repr_contains_shortcut_and_owner(self):
        _set_current_user(self.user)
        self.quick_message.delete()

        log = DeletionLog.objects.get(model_name="QuickMessage")
        self.assertIn(self.quick_message.shortcut, log.object_repr)
        self.assertIn(self.user.email, log.object_repr)

    def test_deletion_log_deleted_by_is_null_when_no_user(self):
        _clear_current_user()
        self.quick_message.delete()

        log = DeletionLog.objects.get(model_name="QuickMessage")
        self.assertIsNone(log.deleted_by)
