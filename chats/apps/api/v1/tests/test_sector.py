from unittest import result
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from chats.apps.api.utils import create_user_and_token
from chats.apps.projects.models import Project
from chats.apps.sectorqueue.models import SectorQueue
from chats.apps.sectors.models import Sector, SectorAuthorization


class SectorTests(APITestCase):
    def setUp(self):
        self.owner, self.owner_token = create_user_and_token("owner")
        self.manager, self.manager_token = create_user_and_token("manager")
        self.user, self.user_token = create_user_and_token("user")
        self.user_2, self.user_2_token = create_user_and_token("user2")
        self.user_3, self.user_3_token = create_user_and_token("user3")

        self.project = Project.objects.create(
            name="Test Project", connect_pk="asdasdas-dad-as-sda-d-ddd"
        )
        self.project_2 = Project.objects.create(
            name="Test Project", connect_pk="asdasdas-dad-as-sda-d-ddd"
        )
        self.sector_1 = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
        )
        self.sector_2 = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=5,
            work_start="07:00",
            work_end="17:00",
        )

        self.sector_3 = Sector.objects.create(
            name="Test Sector",
            project=self.project_2,
            rooms_limit=3,
            work_start="07:00",
            work_end="17:00",
        )

        self.owner_auth = self.project.authorizations.create(user=self.owner, role=1)
        self.manager_auth = self.sector_1.set_user_authorization(self.manager, role=2)
        self.manager_2_auth = self.sector_2.set_user_authorization(self.manager, role=2)
        self.manager_3_auth = self.sector_3.set_user_authorization(self.user_3, role=2)

    def test_retrieve_sector_with_right_project_token(self):
        url = reverse("sector-detail", args=[self.sector_1.uuid])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.manager_token.key)
        response = client.get(url, data={"project": self.project.uuid})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_sector_list_with_right_project_token(self):
        """
        Ensure that the user need to pass a project_id in order to get the sectors related to them
        """
        url = reverse("sector-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.owner_token.key)
        response = client.get(url, data={"project": self.project.uuid})
        results = response.json().get("results")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("count"), 2)
        self.assertEqual(results[0].get("uuid"), str(self.sector_1.uuid))
        self.assertEqual(results[1].get("uuid"), str(self.sector_2.uuid))

    def test_get_sector_list_with_wrong_project_token(self):
        """
        Ensure that an unauthorized user cannot access the sector list of the project
        """
        url = reverse("sector-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.user_3_token.key)
        response = client.get(url, data={"project": self.project.uuid})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("count"), 0)

        response = self.client.get(url, data={"project": self.project.uuid})

    def test_create_sector_with_right_project_token(self):
        url = reverse("sector-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.owner_token.key)
        data = {
            "name": "Finances",
            "rooms_limit": 3,
            "work_start": "11:00",
            "work_end": "19:30",
            "project": str(self.project.uuid),
        }
        response = client.post(url, data=data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update_sector_with_right_project_token(self):
        url = reverse("sector-detail", args=[self.sector_1.uuid])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.owner_token.key)
        response = client.put(url, data={"name": "sector 2 updated"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        sector = Sector.objects.get(uuid=self.sector_1.uuid)

        self.assertEqual("sector 2 updated", sector.name)

    def test_delete_sector_with_right_project_token(self):
        url = reverse("sector-detail", args=[self.sector_1.uuid])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.owner_token.key)
        response = client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        sector = Sector.objects.get(uuid=self.sector_1.uuid)

        self.assertEqual(sector.is_deleted, True)


class SectorTagTests(APITestCase):
    def setUp(self):
        self.owner, self.owner_token = create_user_and_token("owner")
        self.manager, self.manager_token = create_user_and_token("manager")
        self.agent, self.agent_token = create_user_and_token("user")

        self.project = Project.objects.create(
            name="issaquinumehstartupnao", connect_pk="asdasdas-dad-as-sda-d-ddd"
        )

        self.sector_1 = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
        )

        self.tag_1 = self.sector_1.tags.create(name="tag 1")
        self.tag_2 = self.sector_1.tags.create(name="tag 2")

        self.owner_auth = self.project.authorizations.create(
            user=self.owner, role=1
        )  # project: admin role
        self.manager_auth = self.sector_1.set_user_authorization(
            self.manager, role=2
        )  # sector: manager role
        self.agent_auth = self.sector_1.set_user_authorization(
            self.agent, role=1
        )  # sector: agent role

    def list_sector_tag_with_token(self, token):
        url = reverse("sectortag-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + token)
        response = client.get(url, data={"sector": self.sector_1.uuid})
        return response

    def test_list_sector_tags_with_manager_token(self):
        response = self.list_sector_tag_with_token(self.manager_token.key)
        results = response.json().get("results")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("count"), 2)
        self.assertEqual(results[0].get("uuid"), str(self.tag_1.uuid))
        self.assertEqual(results[1].get("uuid"), str(self.tag_2.uuid))

    def test_list_sector_tags_with_agent_token(self):
        response = self.list_sector_tag_with_token(self.agent_token.key)
        results = response.json().get("results")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("count"), 2)
        self.assertEqual(results[0].get("uuid"), str(self.tag_1.uuid))
        self.assertEqual(results[1].get("uuid"), str(self.tag_2.uuid))

    def test_retrieve_sector_tags_with_manager_token(self):
        url = reverse("sectortag-detail", args=[self.tag_1.uuid])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.manager_token.key)
        response = client.get(url, data={"sector": self.sector_1.uuid})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_sector_tags_with_manager_token(self):
        url = reverse("sectortag-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.manager_token.key)
        data = {
            "name": "teste 123",
            "sector": str(self.sector_1.uuid),
        }
        response = client.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update_sector_tags_with_manager_token(self):
        url = reverse("sectortag-detail", args=[self.tag_1.uuid])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.manager_token.key)
        data = {
            "name": "teste 12222223",
        }
        response = client.put(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_sector_tags_with_manager_token(self):
        url = reverse("sectortag-detail", args=[self.tag_1.uuid])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.manager_token.key)
        response = client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class SectorQueueTests(APITestCase):
    def setUp(self):
        self.owner, self.owner_token = create_user_and_token("owner")
        self.manager, self.manager_token = create_user_and_token("manager")
        self.agent, self.agent_token = create_user_and_token("agent")
        self.agent_2, self.agent_2_token = create_user_and_token("agent_2")
        self.user_without_auth, self.user_without_auth_token = create_user_and_token("agent_without_auth")

        self.project = Project.objects.create(
            name="testeproject", connect_pk="asdasdas-dad-as-sda-d-ddd"
        )

        self.sector_1 = Sector.objects.create(
            name="Test Sector",
            project=self.project,
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
        )

        self.sector_2 = Sector.objects.create(
            name="Test Sector Without Auth",
            project=self.project,
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
        )

        self.queue_1 = SectorQueue.objects.create(
            name="suport queue",
            sector=self.sector_1
        )

        self.queue_2 = SectorQueue.objects.create(
            name="suport queue wihtout auth",
            sector=self.sector_2
        )

        self.owner_auth = self.project.authorizations.create(
            user=self.owner, role=1
        )  # project: admin role
        self.manager_auth = self.sector_1.set_user_authorization(
            self.manager, role=2
        )  # sector: manager role
        self.agent_auth = self.queue_1.set_queue_authorization(
            self.agent, role=1
        )  # sector: agent role
        self.agent_auth_2 = self.queue_2.set_queue_authorization(
            self.agent_2, role=1
        )  # sector: agent 2 role

    def list_queue_request(self, token):
        url = reverse("queue-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + token)
        response = client.get(url, data={"sector": self.sector_1.uuid})
        return response

    def test_list_queue_with_agent_token_without_queue_auth(self):
        """
        certifies that users who don't have authorization cannot list queues.
        """
        response = self.list_queue_request(self.user_without_auth_token.key)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['detail'], "You do not have permission to perform this action.")

    def test_list_queue_with_admin_token(self):
        response = self.list_queue_request(self.owner_token.key)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("count"), 2)

    def test_list_queue_with_manager_token(self):
        response = self.list_queue_request(self.manager_token.key)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("count"), 1)

    def test_list_queue_with_agent_token(self):
        response = self.list_queue_request(self.agent_token.key)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("count"), 1)

    def retrieve_queue_request(self, token):
        url = reverse("queue-detail", args=[self.queue_1.uuid])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + token)
        response = client.get(url, data={"sector": self.sector_1.uuid})
        return response

    def test_retrieve_queue_without_queue_auth(self):
        """
        certifies that users who don't have authorization, cannot retrieve queues.
        """
        response = self.retrieve_queue_request(self.user_without_auth_token.key)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['detail'], "You do not have permission to perform this action.")

    def test_retrieve_queue_with_admin_token(self):
        response = self.retrieve_queue_request(self.owner_token.key)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['uuid'], str(self.queue_1.uuid))

    def test_retrieve_queue_with_manager_token(self):
        response = self.retrieve_queue_request(self.manager_token.key)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['uuid'], str(self.queue_1.uuid))

    def test_retrieve_queue_with_agent_token(self):
        response = self.retrieve_queue_request(self.agent_token.key)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['uuid'], str(self.queue_1.uuid))

    def list_queue_auth_request(self, token):
        url = reverse("queue_auth-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + token)
        response = client.get(url, data={"sector": self.sector_1.uuid})
        return response

    def test_list_auth_queue_without_permission(self):
        """
        certifies that users who don't have authorization cannot list queues auth.
        """
        response = self.list_queue_auth_request(self.user_without_auth_token.key)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['detail'], "You do not have permission to perform this action.")

    def test_list_auth_queue_with_admin_token(self):
        response = self.list_queue_auth_request(self.owner_token.key)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("count"), 2)

    def test_list_auth_queue_with_manager_token(self):
        response = self.list_queue_auth_request(self.manager_token.key)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("count"), 1)

    def test_list_auth_queue_with_agent_token(self):
        response = self.list_queue_auth_request(self.agent_token.key)
        results = response.json().get("results")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("count"), 1)
        self.assertEqual(results[0].get("user"), self.agent.id)

    def retrieve_queue_auth_request(self, token):
        url = reverse("queue_auth-detail", args=[self.agent_auth.uuid])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + token)
        response = client.get(url, data={"sector": self.sector_1.uuid})
        return response

    def test_retrieve_auth_queue_without_permission(self):
        """
        certifies that users who don't have authorization, cannot retrieve auth queues.
        """
        response = self.retrieve_queue_auth_request(self.user_without_auth_token.key)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['detail'], "You do not have permission to perform this action.")

    def test_retrieve_auth_queue_with_admin_token(self):
        response = self.list_queue_auth_request(self.owner_token.key)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("count"), 2)

    def test_retrieve_auth_queue_with_manager_token(self):
        response = self.list_queue_auth_request(self.manager_token.key)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("count"), 1)

    def test_retrieve_auth_queue_with_agent_token(self):
        response = self.list_queue_auth_request(self.agent_token.key)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("count"), 1)
