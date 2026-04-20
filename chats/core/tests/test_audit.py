import datetime
from unittest.mock import MagicMock, patch

from django.test import TestCase

from chats.apps.accounts.models import User
from chats.apps.projects.models import Project
from chats.apps.quickmessages.models import QuickMessage
from chats.apps.sectors.models import Sector, SectorHoliday
from chats.core.audit import apply_audit_fields, is_audit_active


# ---------------------------------------------------------------------------
# AuditableMixin — FK columns
# ---------------------------------------------------------------------------


class AuditableMixinFieldsTests(TestCase):
    """
    The mixin only declares the FK columns. These tests make sure the columns
    are persisted when a caller sets them explicitly on the instance.
    """

    def setUp(self):
        self.user = User.objects.create_user(email="audit@test.com", password="x")
        self.other_user = User.objects.create_user(email="other@test.com", password="x")
        self.project = Project.objects.create(name="Audit Project", timezone="UTC")

    def _make_sector(self, **kwargs):
        return Sector.objects.create(
            name=kwargs.pop("name", "Sector Audit"),
            project=self.project,
            rooms_limit=5,
            work_start="08:00",
            work_end="18:00",
            **kwargs,
        )

    def test_created_by_is_persisted_when_set_on_create(self):
        sector = self._make_sector(created_by=self.user, modified_by=self.user)
        sector.refresh_from_db()
        self.assertEqual(sector.created_by, self.user)
        self.assertEqual(sector.modified_by, self.user)

    def test_audit_fields_default_to_null(self):
        sector = self._make_sector()
        self.assertIsNone(sector.created_by)
        self.assertIsNone(sector.modified_by)
        self.assertIsNone(sector.deleted_by)

    def test_modified_by_is_updated_on_save(self):
        sector = self._make_sector(created_by=self.user, modified_by=self.user)
        sector.modified_by = self.other_user
        sector.save()
        sector.refresh_from_db()
        self.assertEqual(sector.modified_by, self.other_user)
        self.assertEqual(sector.created_by, self.user)

    def test_deleted_by_is_persisted_via_sector_holiday_delete(self):
        sector = self._make_sector()
        holiday = SectorHoliday.objects.create(
            sector=sector,
            date=datetime.date(2025, 12, 25),
            day_type=SectorHoliday.CLOSED,
        )
        holiday.deleted_by = self.user
        holiday.modified_by = self.user
        holiday.delete()
        holiday.refresh_from_db()
        self.assertEqual(holiday.deleted_by, self.user)
        self.assertEqual(holiday.modified_by, self.user)


# ---------------------------------------------------------------------------
# is_audit_active helper
# ---------------------------------------------------------------------------


class IsAuditActiveTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="h@test.com", password="x")
        self.project = Project.objects.create(name="H Project", timezone="UTC")

    def _request(self, user=None):
        request = MagicMock()
        request.user = user if user is not None else self.user
        return request

    def test_returns_false_when_project_is_none(self):
        self.assertFalse(is_audit_active(self._request(), None))

    def test_returns_false_when_request_is_none(self):
        self.assertFalse(is_audit_active(None, self.project))

    def test_returns_false_when_user_is_not_authenticated(self):
        anon = MagicMock()
        anon.is_authenticated = False
        self.assertFalse(is_audit_active(self._request(user=anon), self.project))

    @patch("chats.core.audit.is_feature_active", return_value=True)
    def test_returns_true_when_flag_active(self, _):
        self.assertTrue(is_audit_active(self._request(), self.project))

    @patch("chats.core.audit.is_feature_active", return_value=False)
    def test_returns_false_when_flag_inactive(self, _):
        self.assertFalse(is_audit_active(self._request(), self.project))

    @patch(
        "chats.core.audit.is_feature_active",
        side_effect=RuntimeError("flag service down"),
    )
    def test_fails_open_when_flag_service_raises(self, _):
        self.assertTrue(is_audit_active(self._request(), self.project))


# ---------------------------------------------------------------------------
# apply_audit_fields helper (used by viewset direct-save paths)
# ---------------------------------------------------------------------------


class ApplyAuditFieldsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="a@test.com", password="x")
        self.project = Project.objects.create(name="A Project", timezone="UTC")
        self.sector = Sector.objects.create(
            name="A Sector",
            project=self.project,
            rooms_limit=5,
            work_start="08:00",
            work_end="18:00",
        )

    def _request(self):
        request = MagicMock()
        request.user = self.user
        return request

    @patch("chats.core.audit.is_feature_active", return_value=True)
    def test_sets_modified_by_when_flag_on(self, _):
        apply_audit_fields(self.sector, self._request(), self.project)
        self.assertEqual(self.sector.modified_by, self.user)
        self.assertIsNone(self.sector.deleted_by)

    @patch("chats.core.audit.is_feature_active", return_value=True)
    def test_sets_deleted_by_when_on_delete_is_true(self, _):
        apply_audit_fields(
            self.sector, self._request(), self.project, on_delete=True
        )
        self.assertEqual(self.sector.modified_by, self.user)
        self.assertEqual(self.sector.deleted_by, self.user)

    @patch("chats.core.audit.is_feature_active", return_value=False)
    def test_does_nothing_when_flag_off(self, _):
        apply_audit_fields(
            self.sector, self._request(), self.project, on_delete=True
        )
        self.assertIsNone(self.sector.modified_by)
        self.assertIsNone(self.sector.deleted_by)

    def test_does_nothing_when_project_is_none(self):
        apply_audit_fields(self.sector, self._request(), None, on_delete=True)
        self.assertIsNone(self.sector.modified_by)
        self.assertIsNone(self.sector.deleted_by)


# ---------------------------------------------------------------------------
# AuditableModelSerializer (flag gating in the serializer layer)
# ---------------------------------------------------------------------------


class AuditableModelSerializerTests(TestCase):
    """
    Exercise the serializer base class by using SectorSerializer, which now
    inherits AuditableModelSerializer.
    """

    def setUp(self):
        from chats.apps.api.v1.sectors.serializers import SectorSerializer

        self.serializer_class = SectorSerializer
        self.user = User.objects.create_user(email="s@test.com", password="x")
        self.other_user = User.objects.create_user(email="s2@test.com", password="x")
        self.project = Project.objects.create(name="S Project", timezone="UTC")

    def _request(self, user=None):
        request = MagicMock()
        request.user = user if user is not None else self.user
        return request

    def _payload(self, **overrides):
        data = {
            "name": "S Sector",
            "project": str(self.project.uuid),
            "rooms_limit": 5,
            "work_start": "08:00",
            "work_end": "18:00",
        }
        data.update(overrides)
        return data

    def _sector_from_db(self):
        return Sector.objects.get(project=self.project)

    @patch("chats.core.audit.is_feature_active", return_value=True)
    def test_audit_persists_when_flag_on(self, _):
        serializer = self.serializer_class(
            data=self._payload(),
            context={"request": self._request()},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(created_by=self.user, modified_by=self.user)

        sector = self._sector_from_db()
        self.assertEqual(sector.created_by, self.user)
        self.assertEqual(sector.modified_by, self.user)

    @patch("chats.core.audit.is_feature_active", return_value=False)
    def test_audit_dropped_on_create_when_flag_off(self, _):
        serializer = self.serializer_class(
            data=self._payload(),
            context={"request": self._request()},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(created_by=self.user, modified_by=self.user)

        sector = self._sector_from_db()
        self.assertIsNone(sector.created_by)
        self.assertIsNone(sector.modified_by)

    @patch("chats.core.audit.is_feature_active", return_value=True)
    def test_history_preserved_on_update_when_flag_toggles_off(self, mock_flag):
        create_serializer = self.serializer_class(
            data=self._payload(),
            context={"request": self._request()},
        )
        create_serializer.is_valid(raise_exception=True)
        create_serializer.save(created_by=self.user, modified_by=self.user)
        sector = self._sector_from_db()

        mock_flag.return_value = False

        from chats.apps.api.v1.sectors.serializers import SectorUpdateSerializer

        update_serializer = SectorUpdateSerializer(
            instance=sector,
            data={"rooms_limit": 10},
            partial=True,
            context={"request": self._request(user=self.other_user)},
        )
        update_serializer.is_valid(raise_exception=True)
        update_serializer.save(modified_by=self.other_user)

        sector.refresh_from_db()
        self.assertEqual(sector.created_by, self.user)
        self.assertEqual(sector.modified_by, self.user)
        self.assertEqual(sector.rooms_limit, 10)


# ---------------------------------------------------------------------------
# QuickMessage fallback: no sector → no project → flag treated as off
# ---------------------------------------------------------------------------


class QuickMessageAuditTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="qm@test.com", password="x")
        self.project = Project.objects.create(name="QM Project", timezone="UTC")
        self.sector = Sector.objects.create(
            name="QM Sector",
            project=self.project,
            rooms_limit=5,
            work_start="08:00",
            work_end="18:00",
        )

    def _request(self):
        request = MagicMock()
        request.user = self.user
        return request

    def test_audit_is_skipped_when_quick_message_has_no_sector(self):
        """
        Without a sector we cannot resolve a project to evaluate the flag,
        so the serializer must behave as if the flag was off.
        """
        from chats.apps.api.v1.quickmessages.serializers import QuickMessageSerializer

        with patch("chats.core.audit.is_feature_active") as mock_flag:
            serializer = QuickMessageSerializer(
                data={"shortcut": "/oi", "text": "Olá"},
                context={"request": self._request()},
            )
            serializer.is_valid(raise_exception=True)
            serializer.save(
                user=self.user,
                created_by=self.user,
                modified_by=self.user,
            )

        mock_flag.assert_not_called()
        qm = QuickMessage.objects.get(shortcut="/oi")
        self.assertIsNone(qm.created_by)
        self.assertIsNone(qm.modified_by)

    @patch("chats.core.audit.is_feature_active", return_value=True)
    def test_audit_is_written_for_quick_message_with_sector(self, _):
        from chats.apps.api.v1.quickmessages.serializers import QuickMessageSerializer

        serializer = QuickMessageSerializer(
            data={
                "shortcut": "/oi",
                "text": "Olá",
                "sector": str(self.sector.uuid),
            },
            context={"request": self._request()},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(
            user=self.user,
            created_by=self.user,
            modified_by=self.user,
        )

        qm = QuickMessage.objects.get(shortcut="/oi")
        self.assertEqual(qm.created_by, self.user)
        self.assertEqual(qm.modified_by, self.user)
