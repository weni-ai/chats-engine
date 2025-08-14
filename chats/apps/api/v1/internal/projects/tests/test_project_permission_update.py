from django.test import TestCase, RequestFactory
from unittest.mock import patch
from rest_framework.test import force_authenticate
from chats.apps.accounts.models import User
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.api.v1.internal.projects.viewsets import ProjectPermissionViewset

class ProjectPermissionUpdateTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin = User.objects.create(email="admin@acme.com")
        self.target = User.objects.create(email="agent@acme.com")
        self.project = Project.objects.create(name="P", timezone="UTC")

    @patch("chats.apps.api.v1.internal.projects.viewsets.get_user_id_by_email_cached")
    @patch("chats.apps.api.v1.internal.projects.viewsets.persist_keycloak_user_by_email")
    def test_update_uses_user_id_email(self, mock_persist, mock_cache):
        mock_cache.return_value = self.target.pk
        view = ProjectPermissionViewset.as_view({"put": "update"})
        req = self.factory.put("/x", data={"user": "Agent@Acme.com", "role": 1, "project": str(self.project.pk)}, content_type="application/json")
        force_authenticate(req, user=self.admin)
        resp = view(req, uuid="ignored")
        self.assertEqual(resp.status_code, 200)
        perm = ProjectPermission.objects.get(project=self.project, user_id="agent@acme.com")
        self.assertEqual(perm.role, 1)

    @patch("chats.apps.api.v1.internal.projects.viewsets.get_user_id_by_email_cached", return_value=None)
    @patch("chats.apps.api.v1.internal.projects.viewsets.persist_keycloak_user_by_email")
    def test_update_404_when_user_missing(self, _persist, _cache):
        view = ProjectPermissionViewset.as_view({"put": "update"})
        req = self.factory.put("/x", data={"user": "x@acme.com", "role": 1, "project": str(self.project.pk)}, content_type="application/json")
        force_authenticate(req, user=self.admin)
        resp = view(req, uuid="ignored")
        self.assertEqual(resp.status_code, 404)