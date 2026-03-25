import uuid
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase
from django.test import override_settings
from rest_framework.response import Response
from unittest.mock import patch

from chats.apps.accounts.models import User
from chats.apps.core.internal_domains import get_vtex_internal_domains_with_at_symbol
from chats.apps.projects.models import Project
from chats.apps.projects.models.models import ProjectPermission
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.sectors.models import Sector, SectorAuthorization

from chats.apps.projects.tests.decorators import with_project_permission


class QueueTests(APITestCase):
    fixtures = ["chats/fixtures/fixture_sector.json"]

    def setUp(self):
        self.project = Project.objects.get(pk="34a93b52-231e-11ed-861d-0242ac120002")
        self.sector = Sector.objects.get(pk="21aecf8c-0c73-4059-ba82-4343e0cc627c")
        self.manager_user = User.objects.get(pk=8)
        self.manager_token = Token.objects.get(user=self.manager_user)
        self.agent_user = User.objects.get(pk=6)
        self.agent_token = Token.objects.get(user=self.agent_user)
        self.admin_user = User.objects.get(pk=1)
        self.admin_token = Token.objects.get(user=self.admin_user)

        self.queue_1 = Queue.objects.create(name="suport queue", sector=self.sector)

    def list_queue_request(self, token):
        """
        Verify if the list endpoint for queue its returning the correct object.
        """
        url = reverse("queue-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + token)
        response = client.get(url, data={"sector": self.sector.pk})
        return response

    def test_list_queue_with_admin_token(self):
        """
        Verify if the list endpoint for queue its returning the correct object using admin token.
        """
        response = self.list_queue_request(self.admin_token.key)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("count"), 2)

    def test_list_queue_with_manager_token(self):
        """
        Verify if the list endpoint for queue its returning the correct object using manager token.
        """
        response = self.list_queue_request(self.manager_token.key)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("count"), 2)

    def test_list_queue_with_agent_token(self):
        """
        Verify if the list endpoint for queue its returning the correct object using agent token.
        """
        response = self.list_queue_request(self.agent_token.key)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("count"), 2)

    def retrieve_queue_request(self, token):
        """
        Verify if the retrieve endpoint for queue its returning the correct object.
        """
        url = reverse("queue-detail", args=[self.queue_1.pk])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + token)
        response = client.get(url, data={"sector": self.sector.pk})
        return response

    def test_retrieve_queue_with_admin_token(self):
        """
        Verify if the retrieve endpoint for queue its returning the correct object using admin token.
        """
        response = self.retrieve_queue_request(self.admin_token.key)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["uuid"], str(self.queue_1.pk))

    def test_create_queue_with_manager_token(self):
        """
        Verify if the create endpoint for queue its working correctly.
        """
        url = reverse("queue-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.admin_token.key)
        data = {
            "name": "queue created by test",
            "sector": str(self.sector.pk),
        }
        response = client.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update_queue_with_manager_token(self):
        """
        Verify if the update endpoint for queue its working correctly.
        """
        url = reverse("queue-detail", args=[self.queue_1.pk])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.manager_token.key)
        data = {
            "name": "teste 12222223",
        }
        response = client.patch(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_queue_with_manager_token(self):
        """
        Verify if the delete endpoint for queue its working correctly.
        """
        url = reverse("queue-detail", args=[self.queue_1.pk])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.admin_token.key)
        response = client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class BaseTestQueueViewSet(APITestCase):
    def retrieve_queue(self, queue_uuid: str) -> Response:
        url = reverse("queue-detail", args=[queue_uuid])

        return self.client.get(url)

    def list_queues(self) -> Response:
        url = reverse("queue-list")

        return self.client.get(url)

    def create_queue(self, data: dict) -> Response:
        url = reverse("queue-list")

        return self.client.post(url, data=data, format="json")

    def update_queue(self, queue_uuid: str, data: dict) -> Response:
        url = reverse("queue-detail", args=[queue_uuid])

        return self.client.patch(url, data=data, format="json")


class TestQueueViewSetAsAnonymousUser(BaseTestQueueViewSet):
    def test_retrieve_queue(self):
        response = self.retrieve_queue(str(uuid.uuid4()))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_queues(self):
        response = self.list_queues()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_queue(self):
        response = self.create_queue({})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_queue(self):
        response = self.update_queue(str(uuid.uuid4()), {})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestQueueViewSetAsAuthenticatedUser(BaseTestQueueViewSet):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            project=self.project,
            name="Test Sector",
            rooms_limit=1,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)

        self.user = User.objects.create(email="test@test.com")
        self.client.force_authenticate(user=self.user)

    def test_retrieve_queue_without_permission(self):
        response = self.retrieve_queue(self.queue.pk)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch("chats.apps.api.v1.queues.serializers.is_feature_active", return_value=True)
    @with_project_permission()
    def test_retrieve_queue_with_project_permission(self, mock_is_feature_active):
        response = self.retrieve_queue(self.queue.pk)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertIn("queue_limit", response.data)

        queue_limit_info = response.data.get("queue_limit")

        self.assertIn("is_active", queue_limit_info)
        self.assertEqual(queue_limit_info.get("is_active"), False)
        self.assertIn("limit", queue_limit_info)
        self.assertEqual(queue_limit_info.get("limit"), None)

    def test_list_queues_without_permission(self):
        response = self.list_queues()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data.get("results")), 0)

    @patch("chats.apps.api.v1.queues.serializers.is_feature_active", return_value=True)
    @with_project_permission()
    def test_list_queues_with_project_permission(self, mock_is_feature_active):
        mock_is_feature_active.return_value = True
        response = self.list_queues()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data.get("results")), 1)
        self.assertEqual(
            response.data.get("results")[0].get("uuid"), str(self.queue.pk)
        )

        self.assertIn("queue_limit", response.data.get("results")[0])
        queue_limit_info = response.data.get("results")[0].get("queue_limit")

        self.assertIn("is_active", queue_limit_info)
        self.assertEqual(queue_limit_info.get("is_active"), False)
        self.assertIn("limit", queue_limit_info)
        self.assertEqual(queue_limit_info.get("limit"), None)

    @patch("chats.apps.api.v1.queues.serializers.is_feature_active", return_value=True)
    @with_project_permission()
    def test_create_queue(self, mock_is_feature_active):
        mock_is_feature_active.return_value = True
        response = self.create_queue(
            {
                "name": "Testing",
                "sector": str(self.sector.pk),
                "queue_limit": {
                    "is_active": True,
                    "limit": 10,
                },
            }
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data.get("name"), "Testing")

        self.assertEqual(response.data.get("queue_limit").get("is_active"), True)
        self.assertEqual(response.data.get("queue_limit").get("limit"), 10)

    @patch("chats.apps.api.v1.queues.serializers.is_feature_active", return_value=False)
    @with_project_permission()
    def test_create_queue_with_queue_limit_feature_flag_is_off(
        self, mock_is_feature_active
    ):
        mock_is_feature_active.return_value = False
        response = self.create_queue(
            {
                "name": "Testing",
                "sector": str(self.sector.pk),
                "queue_limit": {
                    "is_active": True,
                    "limit": 10,
                },
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["detail"][0].code,
            "queue_limit_feature_flag_is_off",
        )

    @patch("chats.apps.api.v1.queues.serializers.is_feature_active", return_value=True)
    @with_project_permission()
    def test_create_queue_with_invalid_queue_limit(self, mock_is_feature_active):
        mock_is_feature_active.return_value = True
        response = self.create_queue(
            {
                "name": "Testing",
                "sector": str(self.sector.pk),
                "queue_limit": {
                    "is_active": True,
                    "limit": "invalid",
                },
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["queue_limit"]["limit"][0].code, "invalid")

    @patch("chats.apps.api.v1.queues.serializers.is_feature_active", return_value=True)
    @with_project_permission()
    def test_create_queue_without_queue_limit(self, mock_is_feature_active):
        mock_is_feature_active.return_value = True
        response = self.create_queue(
            {
                "name": "Testing",
                "sector": str(self.sector.pk),
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            dict(response.data.get("queue_limit")), {"is_active": False, "limit": None}
        )

    @patch("chats.apps.api.v1.queues.serializers.is_feature_active", return_value=True)
    @with_project_permission()
    def test_update_queue(self, mock_is_feature_active):
        mock_is_feature_active.return_value = True
        payload = {
            "name": "Testing",
            "queue_limit": {
                "is_active": True,
                "limit": 17,
            },
        }

        response = self.update_queue(
            self.queue.pk,
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.queue.refresh_from_db()

        self.assertEqual(
            self.queue.queue_limit, payload.get("queue_limit").get("limit")
        )
        self.assertEqual(
            self.queue.is_queue_limit_active,
            payload.get("queue_limit").get("is_active"),
        )

    @patch("chats.apps.api.v1.queues.serializers.is_feature_active", return_value=False)
    @with_project_permission()
    def test_update_queue_with_queue_limit_feature_flag_is_off(
        self, mock_is_feature_active
    ):
        mock_is_feature_active.return_value = False
        response = self.update_queue(
            self.queue.pk,
            {
                "name": "Testing",
                "queue_limit": {
                    "is_active": True,
                    "limit": 10,
                },
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["detail"][0].code,
            "queue_limit_feature_flag_is_off",
        )

    @patch("chats.apps.api.v1.queues.serializers.is_feature_active", return_value=False)
    @with_project_permission()
    def test_update_queue_with_queue_limit_feature_flag_is_off_and_queue_limit_is_false(
        self, mock_is_feature_active
    ):
        mock_is_feature_active.return_value = False
        response = self.update_queue(
            self.queue.pk,
            {
                "name": "Testing",
                "queue_limit": {
                    "is_active": False,
                    "limit": 10,
                },
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("chats.apps.api.v1.queues.serializers.is_feature_active", return_value=True)
    @with_project_permission()
    def test_update_queue_without_queue_limit(self, mock_is_feature_active):
        mock_is_feature_active.return_value = True
        response = self.update_queue(
            self.queue.pk,
            {
                "name": "Testing",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.queue.refresh_from_db()
        self.assertEqual(self.queue.queue_limit, None)
        self.assertEqual(self.queue.is_queue_limit_active, False)


class QueueTransferAgentsTests(APITestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            project=self.project,
            name="Test Sector",
            rooms_limit=1,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)

        self.user = User.objects.create(email="user1@test.com")

        self.client.force_authenticate(user=self.user)

    def test_transfer_agents_without_project_permission(self):
        url = reverse("queue-transfer-agents", args=[self.queue.pk])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @with_project_permission()
    def test_transfer_agents_with_project_permission(self):
        non_internal_agent = User.objects.create(email="agent@test.com")
        agent_perm = ProjectPermission.objects.create(
            project=self.project,
            user=non_internal_agent,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        QueueAuthorization.objects.create(
            queue=self.queue,
            permission=agent_perm,
            role=QueueAuthorization.ROLE_AGENT,
        )

        non_internal_admin = User.objects.create(email="admin@test.com")
        ProjectPermission.objects.create(
            project=self.project,
            user=non_internal_admin,
            role=ProjectPermission.ROLE_ADMIN,
        )

        non_internal_manager = User.objects.create(email="manager@test.com")
        manager_perm = ProjectPermission.objects.create(
            project=self.project,
            user=non_internal_manager,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        SectorAuthorization.objects.create(
            sector=self.sector,
            permission=manager_perm,
            role=SectorAuthorization.ROLE_MANAGER,
        )

        for domain in get_vtex_internal_domains_with_at_symbol():
            user = User.objects.create(email="internal" + domain)
            ProjectPermission.objects.create(
                project=self.project,
                user=user,
                role=ProjectPermission.ROLE_ADMIN,
            )

        url = reverse("queue-transfer-agents", args=[self.queue.pk])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_emails = [user_data.get("email") for user_data in response.data]

        self.assertIn(non_internal_agent.email, returned_emails)
        self.assertIn(non_internal_admin.email, returned_emails)
        self.assertIn(non_internal_manager.email, returned_emails)
        self.assertIn(self.user.email, returned_emails)

        for domain in get_vtex_internal_domains_with_at_symbol():
            self.assertNotIn("internal" + domain, returned_emails)

    @with_project_permission()
    def test_transfer_agents_filter_offline_returns_only_online_non_internal(self):
        self.project.config = {"filter_offline_agents": True}
        self.project.save(update_fields=["config"])

        online_agent = User.objects.create(email="online-agent@test.com")
        online_agent_perm = ProjectPermission.objects.create(
            project=self.project,
            user=online_agent,
            role=ProjectPermission.ROLE_ATTENDANT,
            status=ProjectPermission.STATUS_ONLINE,
        )
        QueueAuthorization.objects.create(
            queue=self.queue,
            permission=online_agent_perm,
            role=QueueAuthorization.ROLE_AGENT,
        )

        offline_agent = User.objects.create(email="offline-agent@test.com")
        offline_agent_perm = ProjectPermission.objects.create(
            project=self.project,
            user=offline_agent,
            role=ProjectPermission.ROLE_ATTENDANT,
            status=ProjectPermission.STATUS_OFFLINE,
        )
        QueueAuthorization.objects.create(
            queue=self.queue,
            permission=offline_agent_perm,
            role=QueueAuthorization.ROLE_AGENT,
        )

        online_manager = User.objects.create(email="online-manager@test.com")
        online_manager_perm = ProjectPermission.objects.create(
            project=self.project,
            user=online_manager,
            role=ProjectPermission.ROLE_ATTENDANT,
            status=ProjectPermission.STATUS_ONLINE,
        )
        SectorAuthorization.objects.create(
            sector=self.sector,
            permission=online_manager_perm,
            role=SectorAuthorization.ROLE_MANAGER,
        )

        online_admin = User.objects.create(email="online-admin@test.com")
        ProjectPermission.objects.create(
            project=self.project,
            user=online_admin,
            role=ProjectPermission.ROLE_ADMIN,
            status=ProjectPermission.STATUS_ONLINE,
        )

        offline_admin = User.objects.create(email="offline-admin@test.com")
        ProjectPermission.objects.create(
            project=self.project,
            user=offline_admin,
            role=ProjectPermission.ROLE_ADMIN,
            status=ProjectPermission.STATUS_OFFLINE,
        )

        url = reverse("queue-transfer-agents", args=[self.queue.pk])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_emails = [user_data.get("email") for user_data in response.data]

        self.assertIn(online_agent.email, returned_emails)
        self.assertIn(online_manager.email, returned_emails)
        self.assertIn(online_admin.email, returned_emails)

        self.assertNotIn(offline_agent.email, returned_emails)
        self.assertNotIn(offline_admin.email, returned_emails)

    @override_settings(VTEX_INTERNAL_DOMAINS=["vtex.com", "weni.ai"])
    def test_transfer_agents_with_when_user_is_internal(self):
        domains = get_vtex_internal_domains_with_at_symbol()

        self.user.email = "user" + domains[0]
        self.user.save(update_fields=["email"])

        ProjectPermission.objects.create(
            project=self.project,
            user=self.user,
            role=ProjectPermission.ROLE_ADMIN,
        )

        non_internal_agent = User.objects.create(email="agent@test.com")
        agent_perm = ProjectPermission.objects.create(
            project=self.project,
            user=non_internal_agent,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        QueueAuthorization.objects.create(
            queue=self.queue,
            permission=agent_perm,
            role=QueueAuthorization.ROLE_AGENT,
        )

        non_internal_admin = User.objects.create(email="admin@test.com")
        ProjectPermission.objects.create(
            project=self.project,
            user=non_internal_admin,
            role=ProjectPermission.ROLE_ADMIN,
        )

        non_internal_manager = User.objects.create(email="manager@test.com")
        manager_perm = ProjectPermission.objects.create(
            project=self.project,
            user=non_internal_manager,
            role=ProjectPermission.ROLE_ATTENDANT,
        )
        SectorAuthorization.objects.create(
            sector=self.sector,
            permission=manager_perm,
            role=SectorAuthorization.ROLE_MANAGER,
        )

        for domain in get_vtex_internal_domains_with_at_symbol():
            user = User.objects.create(email="internal" + domain)
            ProjectPermission.objects.create(
                project=self.project,
                user=user,
                role=ProjectPermission.ROLE_ADMIN,
            )

        url = reverse("queue-transfer-agents", args=[self.queue.pk])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_emails = [user_data.get("email") for user_data in response.data]

        self.assertIn(non_internal_agent.email, returned_emails)
        self.assertIn(non_internal_admin.email, returned_emails)
        self.assertIn(non_internal_manager.email, returned_emails)
        self.assertIn(self.user.email, returned_emails)

        for domain in get_vtex_internal_domains_with_at_symbol():
            self.assertIn("internal" + domain, returned_emails)
