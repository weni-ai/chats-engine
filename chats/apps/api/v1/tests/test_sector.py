from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from chats.apps.accounts.models import User

from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.queues.models import Queue, QueueAuthorization
from chats.apps.sectors.models import Sector, SectorAuthorization
from chats.apps.rooms.models import Room
from rest_framework.authtoken.models import Token


class ActionsTests(APITestCase):
    fixtures = ['chats/fixtures/fixture_app.json']

    def setUp(self) -> None:
        self.project = Project.objects.get(pk="34a93b52-231e-11ed-861d-0242ac120002")
        self.project_2 = Project.objects.get(pk="32e74fec-0dd7-413d-8062-9659f2e213d2")
        manager_user = User.objects.get(pk=9)
        self.login_token =  Token.objects.get_or_create(user=manager_user)[0]

    def test_get_first_access_status(self):
        url = reverse("project_permission-list")
        url_action = f"{url}verify_access/"
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        response = client.get(url_action, data={"project": self.project.pk})
        self.assertEqual(response.data.get("first_access"), True)

    def test_get_first_access_status_without_permission(self):
        url = reverse("project_permission-list")
        url_action = f"{url}verify_access/"
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        response = client.get(url_action, data={"project": self.project_2.pk})
        self.assertEqual(response.data.get("first_access"), None)
        self.assertEqual(response.data["Detail"], "You dont have permission in this project.")

    def test_update_first_access_status(self):
        url = reverse("project_permission-list")
        url_action = f"{url}update_access/?project=34a93b52-231e-11ed-861d-0242ac120002"
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        response = client.patch(url_action)
        self.assertEqual(response.data.get("first_access"), True)

    def test_patch_first_access_status_without_permission(self):
        url = reverse("project_permission-list")
        url_action = f"{url}update_access/?project=32e74fec-0dd7-413d-8062-9659f2e213d2"
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        response = client.patch(url_action)
        self.assertEqual(response.data.get("first_access"), None)
        self.assertEqual(response.data["Detail"], "You dont have permission in this project.")

    
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
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["is_deleted"], True)


class SectorInternalTests(APITestCase):
    def setUp(self):
        self.owner, self.owner_token = create_user_and_token("owner")
        self.manager, self.manager_token = create_user_and_token("manager")
        self.agent, self.agent_token = create_user_and_token("agent")

        self.project = Project.objects.create(
            name="testeprojectinternal", connect_pk="asdasdas-dad-as-sda-d-ddd"
        )
        self.project_02 = Project.objects.create(
            name="testeprojectinternal_02", connect_pk="asdasdas-dad-as-sda-d-ddd"
        )
        self.sector_1 = Sector.objects.create(
            name="Test Sector 01",
            project=self.project,
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
        )
        self.sector_2 = Sector.objects.create(
            name="Test Sector 02",
            project=self.project,
            rooms_limit=5,
            work_start="07:00",
            work_end="17:00",
        )

        self.owner_auth = self.project.authorizations.create(user=self.owner, role=1)
        self.manager_auth = self.sector_1.set_user_authorization(self.manager, role=2)
        self.agent_auth = self.sector_1.set_user_authorization(self.agent, role=2)

    def test_list_internal_sector_with_admin_token(self):
        url = reverse("sector_internal-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.owner_token.key)
        response = client.get(url, data={"project": self.project.uuid})
        results = response.json().get("results")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("count"), 2)
        self.assertEqual(results[0].get("uuid"), str(self.sector_1.uuid))
        self.assertEqual(results[1].get("uuid"), str(self.sector_2.uuid))

    def test_retrieve_internal_sector_with_admin_token(self):
        url = reverse("sector_internal-detail", args=[self.sector_1.uuid])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.manager_token.key)
        response = client.get(url, data={"project": self.project.uuid})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_internal_sector_with_wrong_project_token(self):
        url = reverse("sector_internal-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.agent_token.key)
        response = client.get(url, data={"project": self.project_02.uuid})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("count"), 0)

        response = self.client.get(url, data={"project": self.project_02.uuid})

    def test_create_internal_sector_with_admin_token(self):
        url = reverse("sector_internal-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.owner_token.key)
        data = {
            "name": "sector test",
            "rooms_limit": 3,
            "work_start": "09:00",
            "work_end": "19:00",
            "project": str(self.project.uuid),
        }
        response = client.post(url, data=data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update_internal_sector_with_admin_token(self):
        url = reverse("sector_internal-detail", args=[self.sector_1.uuid])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.owner_token.key)
        response = client.patch(url, data={"name": "sector updated"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        sector = Sector.objects.get(uuid=self.sector_1.uuid)

        self.assertEqual("sector updated", sector.name)

    def test_delete_internal_sector_with_right_project_token(self):
        url = reverse("sector_internal-detail", args=[self.sector_1.uuid])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.owner_token.key)
        response = client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["is_deleted"], True)


class RoomsExternalTests(APITestCase):
    fixtures = ['chats/fixtures/fixture_app.json']

    def setUp(self) -> None:
        self.queue_1 = Queue.objects.get(uuid="f2519480-7e58-4fc4-9894-9ab1769e29cf")

    def test_create_external_room(self):
        url = reverse("external_rooms-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Bearer f3ce543e-d77e-4508-9140-15c95752a380")
        data = {
            "queue_uuid": str(self.queue_1.uuid),
            "contact": {
                "external_id": "e3955fd5-5705-40cd-b480-b45594b70282",
                "name": "Foo Bar",
                "email": "FooBar@weni.ai",
                "phone": "+250788123123",
                "custom_fields": {}
            }
        }
        response = client.post(url, data=data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


    def test_create_external_room_with_external_uuid(self):
        url = reverse("external_rooms-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Bearer f3ce543e-d77e-4508-9140-15c95752a380")
        data = {
            "queue_uuid": str(self.queue_1.uuid),
            "contact": {
                "external_id": "aec9f84e-3dcd-11ed-b878-0242ac120002",
                "name": "external generator",
                "email": "generator@weni.ai",
                "phone": "+558498984312",
                "custom_fields": {
                    "age": "35"
                }
            }
        }
        response = client.post(url, data=data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["contact"]["name"], "external generator")
        self.assertEqual(response.data["contact"]["external_id"], "aec9f84e-3dcd-11ed-b878-0242ac120002")

    
    def test_create_external_room_editing_contact(self):
        url = reverse("external_rooms-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Bearer f3ce543e-d77e-4508-9140-15c95752a380")
        data = {
            "queue_uuid": str(self.queue_1.uuid),
            "contact": {
                "external_id": "e3955fd5-5705-40cd-b480-b45594b70282",
                "name": "gaules",
                "email": "gaulesr@weni.ai",
                "phone": "+5511985543332",
                "custom_fields": {
                    "age": "40",
                    "prefered_game": "cs-go",
                    "job": "streamer"
                }
            }
        }
        response = client.post(url, data=data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["contact"]["name"], "gaules")
        self.assertEqual(response.data["contact"]["custom_fields"]["age"], "40")
        self.assertEqual(response.data["contact"]["custom_fields"]["prefered_game"], "cs-go")
        self.assertEqual(response.data["contact"]["custom_fields"]["job"], "streamer")


class MsgsExternalTests(APITestCase):
    fixtures = ['chats/fixtures/fixture_app.json']

    def setUp(self) -> None:
        self.room = Room.objects.get(uuid="090da6d1-959e-4dea-994a-41bf0d38ba26")

    def test_create_external_msgs(self):
        url = reverse("external_msgs-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Bearer f3ce543e-d77e-4508-9140-15c95752a380")
        data = {
            "room": self.room.uuid,
            "text": "olá.",
            "direction": "incoming",
            "attachments": [
            {
                "content_type": "string",
                "url": "http://example.com"
            }
            ],
        }
        response = client.post(url, data=data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
