from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from chats.apps.accounts.models import User

from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.sectors.models import Sector, SectorAuthorization
from rest_framework.authtoken.models import Token


class SectorTests(APITestCase):
    fixtures = ['chats/fixtures/fixture_sector.json']

    def setUp(self):
        self.sector = Sector.objects.get(pk='21aecf8c-0c73-4059-ba82-4343e0cc627c')
        self.manager_user = User.objects.get(pk=8)
        self.login_token =  Token.objects.get(user=self.manager_user)

    def test_retrieve_sector_with_right_project_token(self):
        url = reverse("sector-detail", args=[self.sector.pk])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        response = client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_sector_list_with_right_project_token(self):
        """
        Ensure that the user need to pass a project_id in order to get the sectors related to them
        """
        project = Project.objects.get(pk='34a93b52-231e-11ed-861d-0242ac120002')
        sector = Sector.objects.get(pk='21aecf8c-0c73-4059-ba82-4343e0cc627c')
        sector_2 = Sector.objects.get(pk='d3cae43d-cf25-4892-bfa6-0f24a856cfb8')
        manager_user = User.objects.get(pk=8)
        login_token =  Token.objects.get_or_create(user=manager_user)[0]

        url = reverse("sector-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + login_token.key)
        response = client.get(url, data={"project": project.pk})
        results = response.json().get("results")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(results[0].get("uuid"), str(sector.pk))
        self.assertEqual(results[1].get("uuid"), str(sector_2.pk))

    def test_get_sector_list_with_wrong_project_token(self):
        """
        Ensure that an unauthorized user cannot access the sector list of the project
        """
        wrong_user = User.objects.get(pk=1)
        login_token =  Token.objects.get_or_create(user=wrong_user)[0]
        project = Project.objects.get(pk='34a93b52-231e-11ed-861d-0242ac120002')

        url = reverse("sector-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + login_token.key)
        response = client.get(url, data={"project": project.pk})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_sector_with_right_project_token(self):
        manager_user = User.objects.get(pk=8)
        login_token =  Token.objects.get_or_create(user=manager_user)[0]
        project = Project.objects.get(pk='34a93b52-231e-11ed-861d-0242ac120002')

        url = reverse("sector-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + login_token.key)
        data = {
            "name": "Finances",
            "rooms_limit": 3,
            "work_start": "11:00",
            "work_end": "19:30",
            "project": str(project.pk),
        }
        response = client.post(url, data=data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update_sector_with_right_project_token(self):
        sector = Sector.objects.get(pk='21aecf8c-0c73-4059-ba82-4343e0cc627c')
        manager_user = User.objects.get(pk=8)
        login_token =  Token.objects.get_or_create(user=manager_user)[0]

        url = reverse("sector-detail", args=[sector.pk])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + login_token.key)
        response = client.put(url, data={"name": "sector 2 updated"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        sector = Sector.objects.get(pk='21aecf8c-0c73-4059-ba82-4343e0cc627c')
        self.assertEqual("sector 2 updated", sector.name)

    def test_delete_sector_with_right_project_token(self):
        url = reverse("sector-detail", args=[self.sector.pk])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        response = client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        sector = Sector.objects.get(pk='21aecf8c-0c73-4059-ba82-4343e0cc627c')
        self.assertEqual(sector.is_deleted, True)


class SectorTagTests(APITestCase):
    fixtures = ['chats/fixtures/fixture_sector.json']

    def setUp(self):
        self.project = Project.objects.get(pk='34a93b52-231e-11ed-861d-0242ac120002')
        self.sector = Sector.objects.get(pk='21aecf8c-0c73-4059-ba82-4343e0cc627c')
        self.manager_user = User.objects.get(pk=8)
        self.manager_token =  Token.objects.get(user=self.manager_user)
        self.agent_user = User.objects.get(pk=6)
        self.agent_token =  Token.objects.get(user=self.agent_user)

        self.tag_1 = self.sector.tags.create(name="tag 1")
        self.tag_2 = self.sector.tags.create(name="tag 2")

    def list_sector_tag_with_token(self, token):
        url = reverse("sectortag-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + token)
        response = client.get(url, data={"sector": self.sector.pk})
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
        url = reverse("sectortag-detail", args=[self.tag_1.pk])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.manager_token.key)
        response = client.get(url, data={"sector": self.sector.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_sector_tags_with_manager_token(self):
        url = reverse("sectortag-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.manager_token.key)
        data = {
            "name": "teste 123",
            "sector": str(self.sector.uuid),
        }
        response = client.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update_sector_tags_with_manager_token(self):
        url = reverse("sectortag-detail", args=[self.tag_1.pk])
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


class QueueTests(APITestCase):
    fixtures = ['chats/fixtures/fixture_sector.json']

    def setUp(self):
        self.project = Project.objects.get(pk='34a93b52-231e-11ed-861d-0242ac120002')
        self.sector = Sector.objects.get(pk='21aecf8c-0c73-4059-ba82-4343e0cc627c')
        self.manager_user = User.objects.get(pk=8)
        self.manager_token =  Token.objects.get(user=self.manager_user)
        self.agent_user = User.objects.get(pk=6)
        self.agent_token =  Token.objects.get(user=self.agent_user)
        self.admin_user = User.objects.get(pk=1)
        self.admin_token =  Token.objects.get(user=self.admin_user)

        self.queue_1 = Queue.objects.create(
            name="suport queue", sector=self.sector
        )

    def list_queue_request(self, token):
        url = reverse("queue-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + token)
        response = client.get(url, data={"sector": self.sector.pk})
        return response

    def test_list_queue_with_admin_token(self):
        response = self.list_queue_request(self.admin_token.key)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("count"), 2)

    def test_list_queue_with_manager_token(self):
        response = self.list_queue_request(self.manager_token.key)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("count"), 2)

    def test_list_queue_with_agent_token(self):
        response = self.list_queue_request(self.agent_token.key)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("count"), 2)

    def retrieve_queue_request(self, token):
        url = reverse("queue-detail", args=[self.queue_1.pk])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + token)
        response = client.get(url, data={"sector": self.sector.pk})
        return response

    def test_retrieve_queue_with_admin_token(self):
        response = self.retrieve_queue_request(self.admin_token.key)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["uuid"], str(self.queue_1.pk))

    def test_create_queue_with_manager_token(self):
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
        url = reverse("queue-detail", args=[self.queue_1.pk])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.manager_token.key)
        data = {
            "name": "teste 12222223",
        }
        response = client.patch(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_queue_with_manager_token(self):
        url = reverse("queue-detail", args=[self.queue_1.pk])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.admin_token.key)
        response = client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
      

class QueueAuthTests(APITestCase):
    fixtures = ['chats/fixtures/fixture_sector.json']

    def setUp(self):
        self.project = Project.objects.get(pk='34a93b52-231e-11ed-861d-0242ac120002')
        self.sector = Sector.objects.get(pk='21aecf8c-0c73-4059-ba82-4343e0cc627c')
        self.manager_user = User.objects.get(pk=8)
        self.manager_token =  Token.objects.get(user=self.manager_user)
        self.agent_user = User.objects.get(pk=6)
        self.agent_token =  Token.objects.get(user=self.agent_user)
        self.admin_user = User.objects.get(pk=1)
        self.admin_token =  Token.objects.get(user=self.admin_user)
        self.authorization_queue_token = QueueAuthorization.objects.get(permission='e416fd45-2896-43a5-bd7a-5067f03c77fa')

        self.queue_1 = Queue.objects.create(
            name="suport queue", sector=self.sector
        )

    def list_internal_queue_request(self, token):
        url = reverse("queue_auth-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + token)
        response = client.get(url, data={"sector": self.sector.pk})
        return response

    def test_list_auth_queue_with_admin_token(self):
        response = self.list_internal_queue_request(self.admin_token.key)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("count"), 1)

    def retrieve_auth_queue_request(self, token):
        url = reverse("queue_auth-detail", args=[self.authorization_queue_token.pk])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + token)
        response = client.get(url, data={"sector": self.sector})
        return response

    def test_retrieve_auth_queue_with_admin_token(self):
        response = self.retrieve_auth_queue_request(self.admin_token.key)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["uuid"], str(self.authorization_queue_token.pk))

    def test_create_auth_queue_with_admin_token(self):
        url = reverse("queue_auth-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.admin_token.key)
        data = {"role": "1", "queue": str(self.queue_1.pk), "permission": 'e416fd45-2896-43a5-bd7a-5067f03c77fa'}
        response = client.post(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update_auth_queue_with_manager_token(self):
        url = reverse("queue_auth-detail", args=[self.authorization_queue_token.pk])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.manager_token.key)
        data = {
            "queue": str(self.queue_1.pk),
            "permission": '101cb6b3-9de3-4b04-8e60-8a7f42ccba54'
        }
        response = client.patch(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_auth_queue_with_manager_token(self):
        url = reverse("queue_auth-detail", args=[self.authorization_queue_token.pk])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.manager_token.key)
        response = client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
