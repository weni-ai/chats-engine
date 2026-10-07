import json
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from chats.apps.api.v1.multi_agents.views import MultiAgentsView
from chats.apps.projects.models import Project, ProjectPermission

User = get_user_model()

PROJECT_UUID = "550e8400-e29b-41d4-a716-446655440000"
NEXUS_RESPONSE_DATA = {"multi_agents": True}

NEXUS_CLIENT_PATH = (
    "chats.apps.api.v1.internal.rest_clients.nexus_rest_client.NexusRESTClient"
)
SERVICE_CACHE_GET = (
    "chats.apps.api.v1.multi_agents.service.get_nexus_multi_agents_cached"
)


def _make_fake_response(status_code=200, json_data=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else NEXUS_RESPONSE_DATA
    resp.text = json.dumps(
        json_data if json_data is not None else NEXUS_RESPONSE_DATA
    )
    return resp


class FakeRedis:
    def __init__(self):
        self.store = {}

    def get(self, k):
        return self.store.get(k)

    def setex(self, k, ttl, v):
        self.store[k] = str(v).encode() if isinstance(v, int) else v

    def delete(self, k):
        if k in self.store:
            del self.store[k]
        return 1


class ViewTestMixin:
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = MultiAgentsView.as_view()
        self.fake_redis = FakeRedis()

        self.project = Project.objects.create(
            uuid=PROJECT_UUID, name="Test Project", timezone="UTC"
        )
        self.user = User.objects.create_user(email="agent@test.com", password="x")
        self.permission = ProjectPermission.objects.create(
            project=self.project,
            user=self.user,
            role=ProjectPermission.ROLE_ADMIN,
        )
        self.outsider = User.objects.create_user(email="outsider@test.com", password="x")

    def _request(self, user=None):
        url = f"/v1/multi-agents/{PROJECT_UUID}/"
        request = self.factory.get(url)
        force_authenticate(request, user=user or self.user)
        return request


class PermissionTests(ViewTestMixin, TestCase):

    @patch(SERVICE_CACHE_GET, return_value=NEXUS_RESPONSE_DATA)
    def test_user_with_permission_can_get(self, _cache):
        response = self.view(self._request(), project_uuid=PROJECT_UUID)
        self.assertEqual(response.status_code, 200)

    @patch(SERVICE_CACHE_GET, return_value=NEXUS_RESPONSE_DATA)
    def test_user_without_permission_gets_403(self, _cache):
        response = self.view(
            self._request(user=self.outsider), project_uuid=PROJECT_UUID
        )
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_gets_401(self):
        request = self.factory.get(f"/v1/multi-agents/{PROJECT_UUID}/")
        response = self.view(request, project_uuid=PROJECT_UUID)
        self.assertEqual(response.status_code, 401)


class GetTests(ViewTestMixin, TestCase):

    @patch(SERVICE_CACHE_GET, return_value=NEXUS_RESPONSE_DATA)
    def test_returns_cached_data(self, _cache):
        response = self.view(self._request(), project_uuid=PROJECT_UUID)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, NEXUS_RESPONSE_DATA)

    @patch(f"{NEXUS_CLIENT_PATH}.get_multi_agents")
    @patch(SERVICE_CACHE_GET, return_value=None)
    def test_nexus_error_forwards_status(self, _cache, mock_nexus):
        error = {"error": "Project not found"}
        mock_nexus.return_value = _make_fake_response(status_code=404, json_data=error)

        response = self.view(self._request(), project_uuid=PROJECT_UUID)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data, error)

    @patch(f"{NEXUS_CLIENT_PATH}.get_multi_agents")
    @patch(SERVICE_CACHE_GET, return_value=None)
    def test_connection_error_returns_502(self, _cache, mock_nexus):
        mock_nexus.side_effect = ConnectionError("refused")

        response = self.view(self._request(), project_uuid=PROJECT_UUID)
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.data, {"error": "Failed to reach NEXUS API"})

    @patch(f"{NEXUS_CLIENT_PATH}.get_multi_agents")
    @patch("chats.core.cache_utils.get_redis_connection", side_effect=Exception("down"))
    def test_redis_down_falls_back_to_nexus(self, _, mock_nexus):
        mock_nexus.return_value = _make_fake_response()

        response = self.view(self._request(), project_uuid=PROJECT_UUID)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, NEXUS_RESPONSE_DATA)


class CacheIntegrationTests(ViewTestMixin, TestCase):

    @patch("chats.core.cache_utils.get_redis_connection")
    @patch(f"{NEXUS_CLIENT_PATH}.get_multi_agents")
    def test_get_populates_then_serves_from_cache(self, mock_nexus, mock_redis):
        mock_redis.return_value = self.fake_redis
        mock_nexus.return_value = _make_fake_response()

        self.view(self._request(), project_uuid=PROJECT_UUID)
        mock_nexus.assert_called_once()

        mock_nexus.reset_mock()
        response = self.view(self._request(), project_uuid=PROJECT_UUID)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, NEXUS_RESPONSE_DATA)
        mock_nexus.assert_not_called()

    @patch("chats.core.cache_utils.NEXUS_MULTI_AGENTS_CACHE_ENABLED", False)
    @patch(f"{NEXUS_CLIENT_PATH}.get_multi_agents")
    def test_cache_disabled_always_calls_nexus(self, mock_nexus):
        mock_nexus.return_value = _make_fake_response()

        self.view(self._request(), project_uuid=PROJECT_UUID)
        self.view(self._request(), project_uuid=PROJECT_UUID)

        self.assertEqual(mock_nexus.call_count, 2)
