from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.quickmessages.models import QuickMessage
from chats.apps.sectors.models import Sector

User = get_user_model()


class BaseTestSectorQuickMessageV2(APITestCase):
    def list(self, params: dict = None):
        url = reverse("sector-quick-message-v2-list")
        return self.client.get(url, params or {})

    def retrieve(self, uuid: str):
        url = reverse("sector-quick-message-v2-detail", kwargs={"uuid": uuid})
        return self.client.get(url)


class TestSectorQuickMessageV2AsAnonymous(BaseTestSectorQuickMessageV2):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.user = User.objects.create_user(
            email="owner@test.com", password="testpass123"
        )
        self.qm = QuickMessage.objects.create(
            shortcut="hi",
            title="Greeting",
            text="Hello!",
            user=self.user,
            sector=self.sector,
        )

    def test_list_returns_401(self):
        response = self.list({"sector": str(self.sector.uuid)})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_returns_401(self):
        response = self.retrieve(str(self.qm.uuid))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestSectorQuickMessageV2AsAuthenticated(BaseTestSectorQuickMessageV2):
    def setUp(self):
        cache.clear()

        self.user = User.objects.create_user(
            email="agent@test.com", password="testpass123"
        )
        self.project = Project.objects.create(name="Test Project")
        self.project_permission = ProjectPermission.objects.create(
            user=self.user,
            project=self.project,
            role=ProjectPermission.ROLE_ATTENDANT,
        )

        self.sector_a = Sector.objects.create(
            name="Sector A",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        self.sector_b = Sector.objects.create(
            name="Sector B",
            project=self.project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )

        self.qm_a1 = QuickMessage.objects.create(
            shortcut="a1",
            title="QM A1",
            text="Sector A message 1",
            user=self.user,
            sector=self.sector_a,
        )
        self.qm_a2 = QuickMessage.objects.create(
            shortcut="a2",
            title="QM A2",
            text="Sector A message 2",
            user=self.user,
            sector=self.sector_a,
        )
        self.qm_b1 = QuickMessage.objects.create(
            shortcut="b1",
            title="QM B1",
            text="Sector B message 1",
            user=self.user,
            sector=self.sector_b,
        )

        self.client.force_authenticate(user=self.user)

    def tearDown(self):
        cache.clear()

    def test_list_by_sector(self):
        response = self.list({"sector": str(self.sector_a.uuid)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        uuids = {r["uuid"] for r in response.data["results"]}
        self.assertEqual(uuids, {str(self.qm_a1.uuid), str(self.qm_a2.uuid)})

    def test_list_by_project(self):
        response = self.list({"project": str(self.project.uuid)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        uuids = {r["uuid"] for r in response.data["results"]}
        self.assertEqual(
            uuids,
            {str(self.qm_a1.uuid), str(self.qm_a2.uuid), str(self.qm_b1.uuid)},
        )

    def test_list_requires_sector_or_project(self):
        response = self.list()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_rejects_both_sector_and_project(self):
        response = self.list(
            {
                "sector": str(self.sector_a.uuid),
                "project": str(self.project.uuid),
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_without_project_permission_gets_403(self):
        other_user = User.objects.create_user(
            email="other@test.com", password="testpass123"
        )
        self.client.force_authenticate(user=other_user)
        response = self.list({"project": str(self.project.uuid)})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_without_permission_sector_filter_gets_403(self):
        other_user = User.objects.create_user(
            email="noperm@test.com", password="testpass123"
        )
        self.client.force_authenticate(user=other_user)
        response = self.list({"sector": str(self.sector_a.uuid)})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_response_structure(self):
        response = self.list({"sector": str(self.sector_a.uuid)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        item = response.data["results"][0]
        expected_fields = {"uuid", "title", "shortcut", "text", "sector"}
        self.assertEqual(set(item.keys()), expected_fields)
        self.assertIn("uuid", item["sector"])
        self.assertEqual(len(item["sector"]), 1)

    def test_retrieve_single_quick_message(self):
        response = self.retrieve(str(self.qm_a1.uuid))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["uuid"], str(self.qm_a1.uuid))
        self.assertEqual(response.data["title"], "QM A1")
        self.assertEqual(response.data["shortcut"], "a1")
        self.assertEqual(response.data["text"], "Sector A message 1")
        self.assertEqual(response.data["sector"]["uuid"], str(self.sector_a.uuid))

    def test_retrieve_without_permission_gets_403(self):
        other_user = User.objects.create_user(
            email="noretperm@test.com", password="testpass123"
        )
        self.client.force_authenticate(user=other_user)
        response = self.retrieve(str(self.qm_a1.uuid))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_pagination_defaults_to_100(self):
        for i in range(110):
            QuickMessage.objects.create(
                shortcut=f"s{i}",
                title=f"Title {i}",
                text=f"Text {i}",
                user=self.user,
                sector=self.sector_a,
            )

        response = self.list({"sector": str(self.sector_a.uuid)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 100)
        self.assertIsNotNone(response.data.get("next"))

    def test_pagination_custom_limit(self):
        response = self.list(
            {
                "sector": str(self.sector_a.uuid),
                "limit": 1,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_no_write_methods(self):
        url = reverse("sector-quick-message-v2-list")
        detail_url = reverse(
            "sector-quick-message-v2-detail",
            kwargs={"uuid": str(self.qm_a1.uuid)},
        )
        payload = {"shortcut": "x", "text": "y"}

        self.assertEqual(
            self.client.post(url, payload).status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        self.assertEqual(
            self.client.put(detail_url, payload).status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        self.assertEqual(
            self.client.patch(detail_url, payload).status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        self.assertEqual(
            self.client.delete(detail_url).status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def test_cache_invalidation_on_create(self):
        response1 = self.list({"sector": str(self.sector_a.uuid)})
        initial_count = len(response1.data["results"])

        QuickMessage.objects.create(
            shortcut="new",
            title="New QM",
            text="Brand new",
            user=self.user,
            sector=self.sector_a,
        )

        response2 = self.list({"sector": str(self.sector_a.uuid)})
        self.assertEqual(len(response2.data["results"]), initial_count + 1)

    def test_cache_invalidation_on_delete(self):
        response1 = self.list({"sector": str(self.sector_a.uuid)})
        initial_count = len(response1.data["results"])

        self.qm_a1.delete()

        response2 = self.list({"sector": str(self.sector_a.uuid)})
        self.assertEqual(len(response2.data["results"]), initial_count - 1)

    def test_cache_invalidation_on_create_project_filter(self):
        response1 = self.list({"project": str(self.project.uuid)})
        initial_count = len(response1.data["results"])

        QuickMessage.objects.create(
            shortcut="proj_new",
            title="Project New",
            text="New under project",
            user=self.user,
            sector=self.sector_b,
        )

        response2 = self.list({"project": str(self.project.uuid)})
        self.assertEqual(len(response2.data["results"]), initial_count + 1)

    def test_list_does_not_include_personal_quick_messages(self):
        QuickMessage.objects.create(
            shortcut="personal",
            title="Personal",
            text="No sector",
            user=self.user,
            sector=None,
        )
        response = self.list({"project": str(self.project.uuid)})
        shortcuts = {r["shortcut"] for r in response.data["results"]}
        self.assertNotIn("personal", shortcuts)

    def test_list_with_nonexistent_sector_returns_403(self):
        import uuid as uuid_mod

        response = self.list({"sector": str(uuid_mod.uuid4())})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cursor_pagination_structure(self):
        response = self.list({"sector": str(self.sector_a.uuid)})
        self.assertIn("next", response.data)
        self.assertIn("previous", response.data)
        self.assertIn("results", response.data)


class BaseTestQuickMessageV2(APITestCase):
    def list(self, params: dict = None):
        url = reverse("quick-message-v2-list")
        return self.client.get(url, params or {})

    def retrieve(self, uuid: str):
        url = reverse("quick-message-v2-detail", kwargs={"uuid": uuid})
        return self.client.get(url)


class TestQuickMessageV2AsAnonymous(BaseTestQuickMessageV2):
    def setUp(self):
        self.user = User.objects.create_user(
            email="owner@test.com", password="testpass123"
        )
        self.qm = QuickMessage.objects.create(
            shortcut="hi",
            title="Greeting",
            text="Hello!",
            user=self.user,
            sector=None,
        )

    def test_list_returns_401(self):
        response = self.list()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_returns_401(self):
        response = self.retrieve(str(self.qm.uuid))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestQuickMessageV2AsAuthenticated(BaseTestQuickMessageV2):
    def setUp(self):
        cache.clear()

        self.user = User.objects.create_user(
            email="agent@test.com", password="testpass123"
        )

        self.qm1 = QuickMessage.objects.create(
            shortcut="q1",
            title="QM 1",
            text="Personal message 1",
            user=self.user,
            sector=None,
        )
        self.qm2 = QuickMessage.objects.create(
            shortcut="q2",
            title="QM 2",
            text="Personal message 2",
            user=self.user,
            sector=None,
        )

        self.client.force_authenticate(user=self.user)

    def tearDown(self):
        cache.clear()

    def test_list_returns_personal_quick_messages(self):
        response = self.list()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        uuids = {r["uuid"] for r in response.data["results"]}
        self.assertEqual(uuids, {str(self.qm1.uuid), str(self.qm2.uuid)})

    def test_list_excludes_sector_quick_messages(self):
        from chats.apps.projects.models import Project
        from chats.apps.sectors.models import Sector

        project = Project.objects.create(name="Test Project")
        sector = Sector.objects.create(
            name="Test Sector",
            project=project,
            rooms_limit=10,
            work_start="09:00",
            work_end="18:00",
        )
        QuickMessage.objects.create(
            shortcut="sector_qm",
            title="Sector QM",
            text="Should not appear",
            user=self.user,
            sector=sector,
        )

        response = self.list()
        shortcuts = {r["shortcut"] for r in response.data["results"]}
        self.assertNotIn("sector_qm", shortcuts)

    def test_response_structure(self):
        response = self.list()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        item = response.data["results"][0]
        expected_fields = {"uuid", "title", "shortcut", "text"}
        self.assertEqual(set(item.keys()), expected_fields)

    def test_retrieve_single_quick_message(self):
        response = self.retrieve(str(self.qm1.uuid))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["uuid"], str(self.qm1.uuid))
        self.assertEqual(response.data["title"], "QM 1")
        self.assertEqual(response.data["shortcut"], "q1")
        self.assertEqual(response.data["text"], "Personal message 1")

    def test_pagination_defaults_to_100(self):
        for i in range(110):
            QuickMessage.objects.create(
                shortcut=f"s{i}",
                title=f"Title {i}",
                text=f"Text {i}",
                user=self.user,
                sector=None,
            )

        response = self.list()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 100)
        self.assertIsNotNone(response.data.get("next"))

    def test_pagination_custom_limit(self):
        response = self.list({"limit": 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_cursor_pagination_structure(self):
        response = self.list()
        self.assertIn("next", response.data)
        self.assertIn("previous", response.data)
        self.assertIn("results", response.data)

    def test_no_write_methods(self):
        url = reverse("quick-message-v2-list")
        detail_url = reverse(
            "quick-message-v2-detail",
            kwargs={"uuid": str(self.qm1.uuid)},
        )
        payload = {"shortcut": "x", "text": "y"}

        self.assertEqual(
            self.client.post(url, payload).status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        self.assertEqual(
            self.client.put(detail_url, payload).status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        self.assertEqual(
            self.client.patch(detail_url, payload).status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        self.assertEqual(
            self.client.delete(detail_url).status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def test_list_excludes_other_users_quick_messages(self):
        other_user = User.objects.create_user(
            email="other@test.com", password="testpass123"
        )
        QuickMessage.objects.create(
            shortcut="other_qm",
            title="Other user QM",
            text="Should not appear",
            user=other_user,
            sector=None,
        )

        response = self.list()
        uuids = {r["uuid"] for r in response.data["results"]}
        self.assertEqual(uuids, {str(self.qm1.uuid), str(self.qm2.uuid)})

    def test_cache_is_isolated_per_user(self):
        self.list()

        other_user = User.objects.create_user(
            email="other2@test.com", password="testpass123"
        )
        QuickMessage.objects.create(
            shortcut="other_cached",
            title="Other cached",
            text="Only for other user",
            user=other_user,
            sector=None,
        )

        self.client.force_authenticate(user=other_user)
        response = self.list()
        uuids = {r["uuid"] for r in response.data["results"]}
        self.assertNotIn(str(self.qm1.uuid), uuids)
        self.assertEqual(len(response.data["results"]), 1)

    def test_cache_invalidation_on_create(self):
        response1 = self.list()
        initial_count = len(response1.data["results"])

        QuickMessage.objects.create(
            shortcut="new",
            title="New QM",
            text="Brand new",
            user=self.user,
            sector=None,
        )

        response2 = self.list()
        self.assertEqual(len(response2.data["results"]), initial_count + 1)

    def test_cache_invalidation_on_delete(self):
        response1 = self.list()
        initial_count = len(response1.data["results"])

        self.qm1.delete()

        response2 = self.list()
        self.assertEqual(len(response2.data["results"]), initial_count - 1)
