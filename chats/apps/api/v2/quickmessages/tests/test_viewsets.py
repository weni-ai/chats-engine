from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.quickmessages.models import QuickMessage

User = get_user_model()


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
