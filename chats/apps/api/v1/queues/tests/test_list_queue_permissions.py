from unittest.mock import patch

from django.test import RequestFactory, TestCase
from rest_framework.test import force_authenticate

from chats.apps.accounts.models import User
from chats.apps.api.v1.queues.viewsets import QueueViewset
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.queues.models import QueueAuthorization


class ListQueuePermissionsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create(email="admin@acme.com")
        self.project = Project.objects.create(name="P", timezone="UTC")
        self.sector = self.project.sectors.create(
            name="S", rooms_limit=5, work_start="08:00", work_end="18:00"
        )
        self.queue = self.sector.queues.create(name="Q")
        self.perm = ProjectPermission.objects.create(
            project=self.project, user=self.user, role=1
        )
        self.qa = QueueAuthorization.objects.create(
            permission=self.perm, queue=self.queue, role=1
        )

    @patch("chats.apps.api.v1.queues.viewsets.get_user_id_by_email_cached")
    def test_list_queue_permissions_returns_items(self, mock_cache):
        mock_cache.return_value = self.user.pk
        view = QueueViewset.as_view({"get": "list_queue_permissions"})
        req = self.factory.get(
            f"/x?user_email=admin@acme.com&project={self.project.pk}"
        )
        force_authenticate(req, user=self.user)
        resp = view(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data["user_permissions"]), 1)

    @patch(
        "chats.apps.api.v1.queues.viewsets.get_user_id_by_email_cached",
        return_value=None,
    )
    def test_list_queue_permissions_empty_when_user_missing(self, _):
        view = QueueViewset.as_view({"get": "list_queue_permissions"})
        req = self.factory.get(f"/x?user_email=no@acme.com&project={self.project.pk}")
        force_authenticate(req, user=self.user)
        resp = view(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["user_permissions"], [])
