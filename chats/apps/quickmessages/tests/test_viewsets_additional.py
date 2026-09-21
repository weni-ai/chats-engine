from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from chats.apps.accounts.models import User
from chats.apps.api.utils import create_user_and_token
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.quickmessages.models import QuickMessage
from chats.apps.queues.models import Queue
from chats.apps.sectors.models import Sector, SectorAuthorization


class TestQuickMessageOwnerPermissions(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user, token = create_user_and_token("owner")
        self.other = User.objects.create_user(
            email="other@test.com", password="pw"
        )
        self.client.credentials(HTTP_AUTHORIZATION="Token " + token.key)

        self.others_message = QuickMessage.objects.create(
            user=self.other, shortcut="x", text="not mine"
        )

    def test_retrieve_returns_404_for_non_owner(self):
        url = reverse("quickmessage-detail", kwargs={"pk": self.others_message.pk})
        response = self.client.get(url)
        # Non-owners cannot see the message via get_queryset filter -> 404
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TestSectorQuickMessageViewset(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user, token = create_user_and_token("sector-mgr")
        self.client.credentials(HTTP_AUTHORIZATION="Token " + token.key)

        self.project = Project.objects.create(name="SQM Project")
        self.permission = ProjectPermission.objects.create(
            project=self.project,
            user=self.user,
            role=ProjectPermission.ROLE_ADMIN,
        )
        self.sector = Sector.objects.create(
            name="SQM Sector",
            project=self.project,
            rooms_limit=2,
            work_start="09:00",
            work_end="18:00",
        )
        SectorAuthorization.objects.create(
            permission=self.permission, sector=self.sector
        )
        Queue.objects.create(name="SQM Queue", sector=self.sector)
        self.sector_message = QuickMessage.objects.create(
            user=self.user,
            sector=self.sector,
            shortcut="hello",
            text="hi {first_name}",
        )

    def _list_url(self):
        return reverse("sector_quick_message-list")

    def test_list_with_project_filters_by_permission(self):
        response = self.client.get(
            f"{self._list_url()}?project={self.project.uuid}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = (
            response.data["results"]
            if isinstance(response.data, dict) and "results" in response.data
            else response.data
        )
        shortcuts = [item["shortcut"] for item in results]
        self.assertIn("hello", shortcuts)

    def test_list_without_project_raises_api_exception(self):
        response = self.client.get(self._list_url())
        # The viewset raises APIException when there's no permission for the
        # missing/empty project parameter.
        self.assertEqual(
            response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR
        )
