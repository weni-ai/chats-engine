from django.test import TestCase, RequestFactory
from unittest.mock import patch
from rest_framework.test import force_authenticate
from chats.apps.accounts.models import User
from chats.apps.projects.models import Project, ProjectPermission
from chats.apps.sectors.models import Sector
from chats.apps.queues.models import Queue
from chats.apps.discussions.models import Discussion
from chats.apps.discussions.filters.discussion import DiscussionFilter
from chats.apps.discussions.views._discussion_user_actions import DiscussionUserActionsMixin
from chats.apps.rooms.models import Room
from rest_framework.request import Request
from rest_framework.request import Request
from django.test import override_settings
from rest_framework.test import APIRequestFactory
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.request import Request
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser


class DummyView(DiscussionUserActionsMixin):
    def get_object(self):
        return self._obj
    def paginate_queryset(self, qs): return None
    def get_paginated_response(self, data): return None

class DiscussionFiltersAndViewsTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.admin = User.objects.create(email="admin@acme.com")
        self.agent = User.objects.create(email="agent@acme.com")
        self.project = Project.objects.create(name="P", timezone="UTC")
        self.sector = self.project.sectors.create(name="S", rooms_limit=5, work_start="08:00", work_end="18:00")
        self.queue = self.sector.queues.create(name="Q")
        self.perm_admin = ProjectPermission.objects.create(project=self.project, user=self.admin, role=1)
        self.perm_agent = ProjectPermission.objects.create(project=self.project, user=self.agent, role=2)
        self.room = Room.objects.create(queue=self.queue, project_uuid=str(self.project.pk))
        self.discussion = Discussion.objects.create(
            subject="Subj",
            created_by=self.admin,
            room=self.room,
            queue=self.queue,
            is_queued=True,
        )

    @patch("chats.apps.discussions.filters.discussion.get_user_id_by_email_cached", return_value=None)
    def test_discussion_filter_returns_none_on_unknown_email(self, _):
        django_req = self.factory.get("/x?email=unknown@acme.com")
        django_req.user = self.admin
        req = Request(django_req)  # <— importante
        qs = Discussion.objects.all()
        f = DiscussionFilter(data={"project": str(self.project.pk)}, queryset=qs, request=req)
        self.assertFalse(f.qs.exists())


    @patch("chats.apps.discussions.views._discussion_user_actions.get_user_id_by_email_cached")
    @override_settings(DISCUSSION_AGENTS_LIMIT=10)
    def test_add_agents_resolves_user_and_creates(self, mock_cache):
        mock_cache.return_value = self.agent.pk
        view = DummyView()
        view._obj = self.discussion

        # Opção A: form (x-www-form-urlencoded)
        django_req = self.factory.post("/x", {"user_email": "Agent@Acme.com"})
        force_authenticate(django_req, user=self.admin)
        req = Request(django_req, parsers=[FormParser(), MultiPartParser(), JSONParser()])
        resp = view.add_agents(req)
        self.assertEqual(resp.status_code, 201)


        