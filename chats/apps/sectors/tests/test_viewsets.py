import uuid
from unittest.mock import Mock, MagicMock, patch

from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from chats.apps.accounts.models import User
from chats.apps.contacts.models import Contact
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.queues.models import Queue
from chats.apps.rooms.models import Room
from chats.apps.sectors.models import Sector, SectorTag

from chats.apps.projects.tests.decorators import with_project_permission


class SectorTests(APITestCase):
    fixtures = ["chats/fixtures/fixture_sector.json"]

    def setUp(self):
        self.manager_user = User.objects.get(pk=8)
        self.login_token = Token.objects.get(user=self.manager_user)
        self.project = Project.objects.get(pk="34a93b52-231e-11ed-861d-0242ac120002")
        self.sector = Sector.objects.get(pk="21aecf8c-0c73-4059-ba82-4343e0cc627c")
        self.sector_2 = Sector.objects.get(pk="4f88b656-194d-4a83-a166-5d84ba825b8d")
        self.wrong_user = User.objects.get(pk=1)
        self.wrong_login_token = Token.objects.get_or_create(user=self.wrong_user)[0]

    def test_retrieve_sector_with_right_project_token(self):
        """
        Verify if the list endpoint for sector its returning the correct object.
        """
        url = reverse("sector-detail", args=[self.sector.pk])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        response = client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["automatic_message"]["is_active"], False)
        self.assertIsNone(response.data["automatic_message"]["text"])

    def test_retrieve_sector_with_right_project_token_and_automatic_message_active(
        self,
    ):
        """
        Verify if the list endpoint for sector its returning the correct object.
        """
        self.sector.is_automatic_message_active = True
        self.sector.automatic_message_text = "Hello, how can I help you?"
        self.sector.save(
            update_fields=["is_automatic_message_active", "automatic_message_text"]
        )
        url = reverse("sector-detail", args=[self.sector.pk])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        response = client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["automatic_message"]["is_active"], True)
        self.assertEqual(
            response.data["automatic_message"]["text"], "Hello, how can I help you?"
        )

    def test_get_sector_list_with_right_project_token(self):
        """
        Ensure that the user need to pass a project_id in order to get the sectors related to them
        """
        self.sector_2.is_automatic_message_active = True
        self.sector_2.automatic_message_text = "Hello, how can I help you?"
        self.sector_2.save(
            update_fields=["is_automatic_message_active", "automatic_message_text"]
        )
        url = reverse("sector-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        response = client.get(url, data={"project": self.project.pk})
        results = response.json().get("results")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(results[0].get("uuid"), str(self.sector.pk))
        self.assertEqual(results[0].get("automatic_message")["is_active"], False)
        self.assertIsNone(results[0].get("automatic_message")["text"])
        self.assertEqual(results[1].get("uuid"), str(self.sector_2.pk))
        self.assertEqual(results[1].get("automatic_message")["is_active"], True)
        self.assertEqual(
            results[1].get("automatic_message")["text"], "Hello, how can I help you?"
        )

    def test_get_sector_list_with_wrong_project_token(self):
        """
        Ensure that an unauthorized user cannot access the sector list of the project
        """
        url = reverse("sector-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.wrong_login_token.key)
        response = client.get(url, data={"project": self.project.pk})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_sector_with_right_project_token(self):
        """
        Verify if the Project Permission its returning the correct value from first_access field.
        """
        url = reverse("sector-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        data = {
            "name": "Finances",
            "rooms_limit": 3,
            "work_start": "11:00",
            "work_end": "19:30",
            "project": str(self.project.pk),
        }
        response = client.post(url, data=data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["automatic_message"]["is_active"], False)
        self.assertIsNone(response.data["automatic_message"]["text"])

    @patch("chats.apps.api.v1.sectors.serializers.is_feature_active")
    def test_create_sector_with_right_project_token_and_automatic_message_active(
        self,
        mock_is_feature_active,
    ):
        """
        Verify if the endpoint for create in sector is working with correctly.
        """
        mock_is_feature_active.return_value = True
        url = reverse("sector-list")
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        data = {
            "name": "Finances",
            "rooms_limit": 3,
            "work_start": "11:00",
            "work_end": "19:30",
            "project": str(self.project.pk),
            "automatic_message": {
                "is_active": True,
                "text": "Hello, how can I help you?",
            },
        }

        response = client.post(url, data=data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["automatic_message"]["is_active"], True)
        self.assertEqual(
            response.data["automatic_message"]["text"], "Hello, how can I help you?"
        )

    def test_update_sector_with_right_project_token(self):
        """
        Verify if the endpoint for update in sector is working with correctly.
        """
        url = reverse("sector-detail", args=[self.sector.pk])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        response = client.put(url, data={"name": "sector 2 updated"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        sector = Sector.objects.get(pk="21aecf8c-0c73-4059-ba82-4343e0cc627c")
        self.assertEqual("sector 2 updated", sector.name)

    @patch("chats.apps.api.v1.sectors.serializers.is_feature_active")
    def test_update_sector_automatic_message(self, mock_is_feature_active):
        """
        Verify if the endpoint for update in sector is working with correctly.
        """
        mock_is_feature_active.return_value = True
        self.sector.is_automatic_message_active = False
        self.sector.save(update_fields=["is_automatic_message_active"])
        url = reverse("sector-detail", args=[self.sector.pk])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        text = "Hello, how can I help you?"
        response = client.patch(
            url,
            data={
                "automatic_message": {
                    "is_active": True,
                    "text": text,
                },
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["automatic_message"]["is_active"], True)
        self.assertEqual(response.data["automatic_message"]["text"], text)

        self.sector.refresh_from_db()
        self.assertTrue(self.sector.is_automatic_message_active)
        self.assertEqual(self.sector.automatic_message_text, text)

    def test_delete_sector_with_right_project_token(self):
        """
        Verify if the endpoint for delete sector is working with correctly.
        """
        url = reverse("sector-detail", args=[self.sector.pk])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        response = client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    @patch("chats.apps.api.v1.sectors.serializers.is_feature_active")
    def test_update_sector_csat_enabled_when_feature_flag_is_off(
        self, mock_is_feature_active
    ):
        """
        Verify if the endpoint for update in sector is working with correctly.
        """
        mock_is_feature_active.return_value = False
        url = reverse("sector-detail", args=[self.sector.pk])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        response = client.patch(url, data={"is_csat_enabled": True})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["is_csat_enabled"][0].code,
            "csat_feature_flag_is_off",
        )
        self.sector.refresh_from_db()
        self.assertFalse(self.sector.is_csat_enabled)

    @patch("chats.apps.api.v1.sectors.serializers.is_feature_active")
    def test_update_sector_csat_enabled_when_feature_flag_is_on(
        self, mock_is_feature_active
    ):
        """
        Verify if the endpoint for update in sector is working with correctly.
        """
        mock_is_feature_active.return_value = True
        url = reverse("sector-detail", args=[self.sector.pk])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        response = client.patch(url, data={"is_csat_enabled": True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.sector.refresh_from_db()
        self.assertTrue(self.sector.is_csat_enabled)

    def test_update_sector_to_require_tags_when_no_tags_are_present(self):
        """
        Verify if the endpoint for update sector is working with correctly.
        """
        url = reverse("sector-detail", args=[self.sector.pk])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        response = client.patch(url, data={"required_tags": True})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["required_tags"][0].code,
            "sector_must_have_at_least_one_tag_to_require_tags",
        )
        self.sector.refresh_from_db()
        self.assertFalse(self.sector.required_tags)

    def test_update_sector_to_require_tags_when_tags_are_present(self):
        """
        Verify if the endpoint for update sector is working with correctly.
        """
        url = reverse("sector-detail", args=[self.sector.pk])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        SectorTag.objects.create(name="Test Tag", sector=self.sector)
        response = client.patch(url, data={"required_tags": True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.sector.refresh_from_db()
        self.assertTrue(self.sector.required_tags)

    def test_update_sector_with_required_tags_as_false_and_no_tags_are_present(self):
        """
        Verify if the endpoint for update sector is working with correctly.
        """
        url = reverse("sector-detail", args=[self.sector.pk])
        client = self.client
        client.credentials(HTTP_AUTHORIZATION="Token " + self.login_token.key)
        response = client.patch(url, data={"required_tags": False})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.sector.refresh_from_db()
        self.assertFalse(self.sector.required_tags)


class RoomsExternalTests(APITestCase):
    fixtures = ["chats/fixtures/fixture_app.json"]

    def setUp(self) -> None:
        self.queue_1 = Queue.objects.get(uuid="f2519480-7e58-4fc4-9894-9ab1769e29cf")

    @patch("chats.apps.sectors.models.Sector.is_attending", return_value=True)
    @patch("chats.apps.projects.usecases.send_room_info.RoomInfoUseCase.get_room")
    def test_create_external_room(self, mock_get_room, mock_is_attending):
        mock_get_room.return_value = None
        url = reverse("external_rooms-list")
        client = self.client
        client.credentials(
            HTTP_AUTHORIZATION="Bearer f3ce543e-d77e-4508-9140-15c95752a380"
        )
        data = {
            "queue_uuid": str(self.queue_1.uuid),
            "contact": {
                "external_id": "e3955fd5-5705-40cd-b480-b45594b70299",
                "name": "Foo Bar",
                "email": "FooBar@weni.ai",
                "phone": "+250788123123",
                "custom_fields": {},
            },
        }
        response = client.post(url, data=data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch("chats.apps.sectors.models.Sector.is_attending", return_value=True)
    @patch("chats.apps.projects.usecases.send_room_info.RoomInfoUseCase.get_room")
    def test_create_external_room_with_external_uuid(
        self, mock_get_room, mock_is_attending
    ):
        mock_get_room.return_value = None
        url = reverse("external_rooms-list")
        client = self.client
        client.credentials(
            HTTP_AUTHORIZATION="Bearer f3ce543e-d77e-4508-9140-15c95752a380"
        )
        data = {
            "queue_uuid": str(self.queue_1.uuid),
            "contact": {
                "external_id": "aec9f84e-3dcd-11ed-b878-0242ac190012",
                "name": "external generator",
                "email": "generator@weni.ai",
                "phone": "+558498984312",
                "custom_fields": {"age": "35"},
            },
        }
        response = client.post(url, data=data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["contact"]["name"], "external generator")
        self.assertEqual(
            response.data["contact"]["external_id"],
            "aec9f84e-3dcd-11ed-b878-0242ac190012",
        )

    @patch("chats.apps.sectors.models.Sector.is_attending", return_value=True)
    @patch("chats.apps.projects.usecases.send_room_info.RoomInfoUseCase.get_room")
    def test_create_external_room_editing_contact(
        self, mock_get_room, mock_is_attending
    ):
        mock_get_room.return_value = None
        url = reverse("external_rooms-list")
        client = self.client
        client.credentials(
            HTTP_AUTHORIZATION="Bearer f3ce543e-d77e-4508-9140-15c95752a380"
        )
        contact = Contact.objects.exclude(rooms__is_active=True).first()
        data = {
            "queue_uuid": str(self.queue_1.uuid),
            "contact": {
                "external_id": contact.external_id,
                "name": "gaules",
                "email": "gaulesr@weni.ai",
                "phone": "+5511985543332",
                "custom_fields": {
                    "age": "40",
                    "prefered_game": "cs-go",
                    "job": "streamer",
                },
            },
        }
        response = client.post(url, data=data, format="json")
        contact.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(contact.name, "gaules")
        self.assertEqual(
            contact.custom_fields,
            {
                "age": "40",
                "prefered_game": "cs-go",
                "job": "streamer",
            },
        )


class MsgsExternalTests(APITestCase):
    fixtures = ["chats/fixtures/fixture_app.json"]

    def setUp(self) -> None:
        self.room = Room.objects.get(uuid="090da6d1-959e-4dea-994a-41bf0d38ba26")

    def test_create_external_msgs(self):
        url = reverse("external_message-list")
        client = self.client
        client.credentials(
            HTTP_AUTHORIZATION="Bearer f3ce543e-d77e-4508-9140-15c95752a380"
        )
        data = {
            "room": self.room.uuid,
            "text": "olá.",
            "direction": "incoming",
            "attachments": [{"content_type": "string", "url": "http://example.com"}],
        }
        response = client.post(url, data=data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class SectorTicketerCreationTests(APITestCase):
    """
    Tests to validate that ticketers are created correctly based on project type:
    - Principal project: ticketer created ONLY in secondary project
    - Normal project: ticketer created in own project
    """

    def setUp(self):
        self.user = User.objects.create(
            email="admin@test.com", first_name="Admin", last_name="User"
        )
        self.token = Token.objects.create(user=self.user)

        self.org_uuid = str(uuid.uuid4())

        self.principal_project = Project.objects.create(
            uuid=str(uuid.uuid4()),
            name="Principal Project",
            org=self.org_uuid,
            config={"its_principal": True},
            timezone="America/Sao_Paulo",
            date_format="D",
        )

        self.secondary_project = Project.objects.create(
            uuid=str(uuid.uuid4()),
            name="Secondary Project",
            org=self.org_uuid,
            config={"its_principal": False},
            timezone="America/Sao_Paulo",
            date_format="D",
        )

        self.normal_project = Project.objects.create(
            uuid=str(uuid.uuid4()),
            name="Normal Project",
            org=str(uuid.uuid4()),
            config={},
            timezone="America/Sao_Paulo",
            date_format="D",
        )

        ProjectPermission.objects.create(
            user=self.user,
            project=self.principal_project,
            role=ProjectPermission.ROLE_ADMIN,
        )

        ProjectPermission.objects.create(
            user=self.user,
            project=self.normal_project,
            role=ProjectPermission.ROLE_ADMIN,
        )

    @patch("chats.apps.api.v1.sectors.viewsets.settings")
    @patch(
        "chats.apps.api.v1.sectors.viewsets.IntegratedTicketers.integrate_individual_ticketer"
    )
    @patch("chats.apps.api.v1.sectors.viewsets.FlowRESTClient.create_ticketer")
    def test_principal_project_creates_ticketer_only_in_secondary(
        self, mock_create_ticketer, mock_integrate_individual, mock_settings
    ):
        """
        When creating a sector in a principal project, should create ticketer
        ONLY in secondary project (via integrate_individual_ticketer),
        NOT in principal project.
        """
        mock_settings.USE_WENI_FLOWS = True
        mock_integrate_individual.return_value = {"status": "success"}

        url = reverse("sector-list")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

        data = {
            "name": "Test Sector Principal",
            "rooms_limit": 5,
            "work_start": "08:00",
            "work_end": "18:00",
            "project": str(self.principal_project.uuid),
            "secondary_project": {"uuid": str(self.secondary_project.uuid)},
        }

        response = self.client.post(url, data=data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        mock_create_ticketer.assert_not_called()

        mock_integrate_individual.assert_called_once()
        call_args = mock_integrate_individual.call_args
        self.assertEqual(str(call_args[0][0].uuid), str(self.principal_project.uuid))
        self.assertEqual(
            call_args[0][1], {"uuid": str(self.secondary_project.uuid)}
        )

    @patch(
        "chats.apps.api.v1.sectors.viewsets.IntegratedTicketers.integrate_individual_ticketer"
    )
    @patch("chats.apps.api.v1.sectors.viewsets.FlowRESTClient.create_ticketer")
    @patch("chats.apps.api.v1.sectors.viewsets.settings")
    def test_normal_project_creates_ticketer_in_own_project(
        self, mock_settings, mock_create_ticketer, mock_integrate_individual
    ):
        """
        When creating a sector in a normal project (not principal),
        should create ticketer in own project via FlowRESTClient,
        NOT call integrate_individual_ticketer.
        """
        mock_settings.USE_WENI_FLOWS = True

        mock_response = Mock()
        mock_response.status_code = status.HTTP_201_CREATED
        mock_create_ticketer.return_value = mock_response

        url = reverse("sector-list")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

        data = {
            "name": "Test Sector Normal",
            "rooms_limit": 5,
            "work_start": "08:00",
            "work_end": "18:00",
            "project": str(self.normal_project.uuid),
        }

        response = self.client.post(url, data=data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        mock_integrate_individual.assert_not_called()

        mock_create_ticketer.assert_called_once()
        call_kwargs = mock_create_ticketer.call_args[1]
        self.assertEqual(call_kwargs["project_uuid"], str(self.normal_project.uuid))

    @patch("chats.apps.api.v1.sectors.viewsets.settings")
    @patch(
        "chats.apps.api.v1.sectors.viewsets.IntegratedTicketers.integrate_individual_ticketer"
    )
    @patch("chats.apps.api.v1.sectors.viewsets.FlowRESTClient.create_ticketer")
    def test_principal_project_does_not_create_duplicate_ticketers(
        self, mock_create_ticketer, mock_integrate_individual, mock_settings
    ):
        """
        Regression test: ensure that principal projects don't create
        ticketers in both principal AND secondary projects (the bug that was fixed).
        Only secondary project should have the ticketer created.
        """
        mock_settings.USE_WENI_FLOWS = True
        mock_integrate_individual.return_value = {"status": "success"}

        url = reverse("sector-list")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

        data = {
            "name": "Test Sector No Duplicate",
            "rooms_limit": 5,
            "work_start": "08:00",
            "work_end": "18:00",
            "project": str(self.principal_project.uuid),
            "secondary_project": {"uuid": str(self.secondary_project.uuid)},
        }

        response = self.client.post(url, data=data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(mock_create_ticketer.call_count, 0)
        self.assertEqual(mock_integrate_individual.call_count, 1)


class SectorEndAllChatsTests(APITestCase):

    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            project=self.project,
            name="Test Sector",
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue = Queue.objects.create(name="Test Queue", sector=self.sector)
        self.queue_2 = Queue.objects.create(
            name="Test Queue 2", sector=self.sector
        )
        self.contact = Contact.objects.create(
            external_id="ext-1", name="Contact 1"
        )
        self.contact_2 = Contact.objects.create(
            external_id="ext-2", name="Contact 2"
        )

        self.user = User.objects.create(email="admin@endall.test")
        self.agent = User.objects.create(email="agent@endall.test")
        self.client.force_authenticate(user=self.user)

    def _delete_sector(self, sector_uuid, end_all_chats=False):
        url = reverse("sector-detail", args=[sector_uuid])
        if end_all_chats:
            url += "?end_all_chats=true"
        return self.client.delete(url)

    @with_project_permission()
    def test_delete_sector_without_flag_does_not_close_rooms(self):
        room = Room.objects.create(
            contact=self.contact,
            queue=self.queue,
            user=self.agent,
            is_active=True,
        )
        response = self._delete_sector(self.sector.uuid)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        room.refresh_from_db()
        self.assertTrue(room.is_active)

    @with_project_permission()
    def test_delete_sector_with_flag_closes_ongoing_rooms(self):
        room = Room.objects.create(
            contact=self.contact,
            queue=self.queue,
            user=self.agent,
            is_active=True,
        )
        response = self._delete_sector(self.sector.uuid, end_all_chats=True)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        room.refresh_from_db()
        self.assertFalse(room.is_active)
        self.assertEqual(room.ended_by, "sector_deleted")

    @with_project_permission()
    def test_delete_sector_with_flag_closes_waiting_rooms(self):
        room = Room.objects.create(
            contact=self.contact,
            queue=self.queue,
            user=None,
            is_active=True,
        )
        response = self._delete_sector(self.sector.uuid, end_all_chats=True)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        room.refresh_from_db()
        self.assertFalse(room.is_active)

    @with_project_permission()
    def test_delete_sector_with_flag_closes_rooms_across_all_queues(self):
        room_q1 = Room.objects.create(
            contact=self.contact,
            queue=self.queue,
            user=self.agent,
            is_active=True,
        )
        room_q2 = Room.objects.create(
            contact=self.contact_2,
            queue=self.queue_2,
            user=None,
            is_active=True,
        )
        response = self._delete_sector(self.sector.uuid, end_all_chats=True)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        room_q1.refresh_from_db()
        room_q2.refresh_from_db()
        self.assertFalse(room_q1.is_active)
        self.assertFalse(room_q2.is_active)

    @with_project_permission()
    def test_delete_sector_with_flag_no_active_rooms_succeeds(self):
        response = self._delete_sector(self.sector.uuid, end_all_chats=True)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Sector.objects.filter(uuid=self.sector.uuid).exists())

    @with_project_permission()
    def test_delete_sector_with_flag_skips_already_closed_rooms(self):
        closed_room = Room.objects.create(
            contact=self.contact,
            queue=self.queue,
            user=self.agent,
            is_active=False,
        )
        active_room = Room.objects.create(
            contact=self.contact_2,
            queue=self.queue,
            user=None,
            is_active=True,
        )
        response = self._delete_sector(self.sector.uuid, end_all_chats=True)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        active_room.refresh_from_db()
        self.assertFalse(active_room.is_active)
        closed_room.refresh_from_db()
        self.assertFalse(closed_room.is_active)


class SectorTransferOnDeleteTests(APITestCase):

    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.sector = Sector.objects.create(
            project=self.project,
            name="Sector To Delete",
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
        )
        self.queue_1 = Queue.objects.create(
            name="Queue 1", sector=self.sector
        )
        self.queue_2 = Queue.objects.create(
            name="Queue 2", sector=self.sector
        )

        self.other_sector = Sector.objects.create(
            project=self.project,
            name="Other Sector",
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
        )
        self.target_queue = Queue.objects.create(
            name="Target Queue", sector=self.other_sector
        )

        self.contact = Contact.objects.create(
            external_id="ext-transfer-s1", name="Contact ST1"
        )
        self.contact_2 = Contact.objects.create(
            external_id="ext-transfer-s2", name="Contact ST2"
        )
        self.contact_3 = Contact.objects.create(
            external_id="ext-transfer-s3", name="Contact ST3"
        )

        self.user = User.objects.create(email="admin@transfer-sector.test")
        self.agent = User.objects.create(email="agent@transfer-sector.test")
        self.client.force_authenticate(user=self.user)

    def _delete_sector(
        self, sector_uuid, transfer_to_queue=None, end_all_chats=False
    ):
        url = reverse("sector-detail", args=[sector_uuid])
        params = []
        if transfer_to_queue:
            params.append(f"transfer_to_queue={transfer_to_queue}")
        if end_all_chats:
            params.append("end_all_chats=true")
        if params:
            url += "?" + "&".join(params)
        return self.client.delete(url)

    @with_project_permission()
    def test_transfer_succeeds_and_sector_is_deleted(self):
        room = Room.objects.create(
            contact=self.contact,
            queue=self.queue_1,
            user=self.agent,
            is_active=True,
        )
        response = self._delete_sector(
            self.sector.uuid, transfer_to_queue=self.target_queue.uuid
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_deleted"])
        self.assertIsNotNone(response.data["transfer"])
        self.assertEqual(response.data["transfer"]["success_count"], 1)
        self.assertEqual(response.data["transfer"]["failed_count"], 0)

        room.refresh_from_db()
        self.assertEqual(room.queue, self.target_queue)
        self.assertTrue(room.is_active)
        self.assertFalse(Sector.objects.filter(uuid=self.sector.uuid).exists())

    @with_project_permission()
    def test_transfer_failure_aborts_deletion(self):
        room = Room.objects.create(
            contact=self.contact,
            queue=self.queue_1,
            user=self.agent,
            is_active=True,
        )
        with patch(
            "chats.apps.api.v1.sectors.viewsets.BulkTransferService.transfer"
        ) as mock_transfer:
            mock_result = MagicMock()
            mock_result.failed_count = 1
            mock_result.success_count = 0
            mock_result.to_dict.return_value = {
                "success_count": 0,
                "failed_count": 1,
                "total_processed": 1,
                "errors": ["Room failed"],
                "failed_rooms": [str(room.uuid)],
                "has_more_errors": False,
            }
            mock_transfer.return_value = mock_result

            response = self._delete_sector(
                self.sector.uuid, transfer_to_queue=self.target_queue.uuid
            )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("transfer", response.data)
        self.assertEqual(response.data["transfer"]["failed_count"], 1)
        self.assertTrue(Sector.objects.filter(uuid=self.sector.uuid).exists())

    @with_project_permission()
    def test_target_queue_belongs_to_sector_being_deleted(self):
        response = self._delete_sector(
            self.sector.uuid, transfer_to_queue=self.queue_1.uuid
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(Sector.objects.filter(uuid=self.sector.uuid).exists())

    @with_project_permission()
    def test_target_queue_not_found(self):
        response = self._delete_sector(
            self.sector.uuid, transfer_to_queue=str(uuid.uuid4())
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Sector.objects.filter(uuid=self.sector.uuid).exists())

    @with_project_permission()
    def test_target_queue_in_different_project(self):
        other_project = Project.objects.create(name="Other Project")
        other_sector = Sector.objects.create(
            project=other_project,
            name="Other Sector Foreign",
            rooms_limit=5,
            work_start="09:00",
            work_end="18:00",
        )
        foreign_queue = Queue.objects.create(
            name="Foreign Queue", sector=other_sector
        )
        response = self._delete_sector(
            self.sector.uuid, transfer_to_queue=foreign_queue.uuid
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(Sector.objects.filter(uuid=self.sector.uuid).exists())

    @with_project_permission()
    def test_transfer_and_end_all_chats_are_mutually_exclusive(self):
        response = self._delete_sector(
            self.sector.uuid,
            transfer_to_queue=self.target_queue.uuid,
            end_all_chats=True,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(Sector.objects.filter(uuid=self.sector.uuid).exists())

    @with_project_permission()
    def test_transfer_no_active_rooms_deletes_sector(self):
        response = self._delete_sector(
            self.sector.uuid, transfer_to_queue=self.target_queue.uuid
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_deleted"])
        self.assertIsNone(response.data["transfer"])
        self.assertFalse(Sector.objects.filter(uuid=self.sector.uuid).exists())

    @with_project_permission()
    def test_transfer_rooms_across_multiple_queues_in_sector(self):
        room_q1 = Room.objects.create(
            contact=self.contact,
            queue=self.queue_1,
            user=self.agent,
            is_active=True,
        )
        room_q2 = Room.objects.create(
            contact=self.contact_2,
            queue=self.queue_2,
            user=None,
            is_active=True,
        )
        response = self._delete_sector(
            self.sector.uuid, transfer_to_queue=self.target_queue.uuid
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["transfer"]["success_count"], 2)

        room_q1.refresh_from_db()
        room_q2.refresh_from_db()
        self.assertEqual(room_q1.queue, self.target_queue)
        self.assertEqual(room_q2.queue, self.target_queue)
        self.assertTrue(room_q1.is_active)
        self.assertTrue(room_q2.is_active)
