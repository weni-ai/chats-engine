import uuid

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from chats.apps.accounts.models import User
from chats.apps.projects.models import Project


def _names_from_response(response):
    payload = response.data
    if isinstance(payload, dict) and "results" in payload:
        return [p["name"] for p in payload["results"]]
    return [p["name"] for p in payload]


class TestOrgProjectViewSet(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="org@test.com", password="pw")
        self.client.force_authenticate(user=self.user)

        self.org_uuid = str(uuid.uuid4())
        self.principal = Project.objects.create(
            name="Principal",
            org=self.org_uuid,
            config={"its_principal": True},
        )
        self.secondary = Project.objects.create(
            name="Secondary",
            org=self.org_uuid,
            config={"its_principal": False},
        )
        self.other_org_project = Project.objects.create(
            name="OtherOrg",
            org=str(uuid.uuid4()),
            config={"its_principal": True},
        )

    def _list(self, params=""):
        return self.client.get(f"/v1/org/{self.org_uuid}/projects/{params}")

    def test_lists_only_projects_of_org(self):
        response = self._list()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = set(_names_from_response(response))
        self.assertEqual(names, {"Principal", "Secondary"})

    def test_filter_its_principal_true(self):
        response = self._list("?its_principal=true")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = _names_from_response(response)
        self.assertEqual(names, ["Principal"])

    def test_filter_its_principal_false(self):
        response = self._list("?its_principal=false")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = _names_from_response(response)
        self.assertEqual(names, ["Secondary"])
