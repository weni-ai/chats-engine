import json
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from chats.apps.api.v1.human_support.views import HumanSupportNexusSettingsView
from chats.apps.projects.models import Project, ProjectPermission

User = get_user_model()

PROJECT_UUID = "550e8400-e29b-41d4-a716-446655440000"
NEXUS_RESPONSE_DATA = {
    "human_support": True,
    "human_support_prompt": "Aguarde enquanto conectamos você com um atendente.",
}

NEXUS_CLIENT_PATH = (
    "chats.apps.api.v1.internal.rest_clients.nexus_rest_client.NexusRESTClient"
)
SERVICE_CACHE_GET = (
    "chats.apps.api.v1.human_support.service.get_nexus_settings_cached"
)


def _make_fake_response(status_code=200, json_data=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or NEXUS_RESPONSE_DATA
    resp.text = json.dumps(json_data or NEXUS_RESPONSE_DATA)
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
        self.view = HumanSupportNexusSettingsView.as_view()
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

    def _request(self, method="get", data=None, user=None):
        url = f"/v1/project/{PROJECT_UUID}/human-support/"
        if method == "get":
            request = self.factory.get(url)
        else:
            request = self.factory.patch(
                url,
                data=json.dumps(data) if data else None,
                content_type="application/json",
            )
        force_authenticate(request, user=user or self.user)
        return request


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------


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
        request = self.factory.get(f"/v1/project/{PROJECT_UUID}/human-support/")
        response = self.view(request, project_uuid=PROJECT_UUID)
        self.assertEqual(response.status_code, 401)

    @patch(f"{NEXUS_CLIENT_PATH}.patch_human_support")
    def test_outsider_cannot_patch(self, mock_nexus):
        mock_nexus.return_value = _make_fake_response()
        response = self.view(
            self._request("patch", data={"human_support": True}, user=self.outsider),
            project_uuid=PROJECT_UUID,
        )
        self.assertEqual(response.status_code, 403)
        mock_nexus.assert_not_called()


# ---------------------------------------------------------------------------
# GET
# ---------------------------------------------------------------------------


class GetTests(ViewTestMixin, TestCase):

    @patch(SERVICE_CACHE_GET, return_value=NEXUS_RESPONSE_DATA)
    def test_returns_cached_data(self, _cache):
        response = self.view(self._request(), project_uuid=PROJECT_UUID)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, NEXUS_RESPONSE_DATA)

    @patch(f"{NEXUS_CLIENT_PATH}.get_human_support")
    @patch(SERVICE_CACHE_GET, return_value=None)
    def test_nexus_error_forwards_status(self, _cache, mock_nexus):
        error = {"error": "Project not found"}
        mock_nexus.return_value = _make_fake_response(status_code=404, json_data=error)

        response = self.view(self._request(), project_uuid=PROJECT_UUID)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data, error)

    @patch(f"{NEXUS_CLIENT_PATH}.get_human_support")
    @patch(SERVICE_CACHE_GET, return_value=None)
    def test_connection_error_returns_502(self, _cache, mock_nexus):
        mock_nexus.side_effect = ConnectionError("refused")

        response = self.view(self._request(), project_uuid=PROJECT_UUID)
        self.assertEqual(response.status_code, 502)

    @patch(f"{NEXUS_CLIENT_PATH}.get_human_support")
    @patch("chats.core.cache_utils.get_redis_connection", side_effect=Exception("down"))
    def test_redis_down_falls_back_to_nexus(self, _, mock_nexus):
        mock_nexus.return_value = _make_fake_response()

        response = self.view(self._request(), project_uuid=PROJECT_UUID)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, NEXUS_RESPONSE_DATA)


# ---------------------------------------------------------------------------
# PATCH
# ---------------------------------------------------------------------------


class PatchTests(ViewTestMixin, TestCase):

    @patch(f"{NEXUS_CLIENT_PATH}.patch_human_support")
    def test_success(self, mock_nexus):
        updated = {"human_support": True, "human_support_prompt": "Updated"}
        mock_nexus.return_value = _make_fake_response(json_data=updated)

        response = self.view(
            self._request("patch", data=updated), project_uuid=PROJECT_UUID
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, updated)

    @patch(f"{NEXUS_CLIENT_PATH}.patch_human_support")
    def test_only_human_support(self, mock_nexus):
        payload = {"human_support": False}
        mock_nexus.return_value = _make_fake_response(
            json_data={"human_support": False, "human_support_prompt": "existing"}
        )

        response = self.view(
            self._request("patch", data=payload), project_uuid=PROJECT_UUID
        )
        self.assertEqual(response.status_code, 200)
        mock_nexus.assert_called_once_with(PROJECT_UUID, payload)

    @patch(f"{NEXUS_CLIENT_PATH}.patch_human_support")
    def test_only_prompt(self, mock_nexus):
        payload = {"human_support_prompt": "New prompt"}
        mock_nexus.return_value = _make_fake_response(
            json_data={"human_support": True, "human_support_prompt": "New prompt"}
        )

        response = self.view(
            self._request("patch", data=payload), project_uuid=PROJECT_UUID
        )
        self.assertEqual(response.status_code, 200)
        mock_nexus.assert_called_once_with(PROJECT_UUID, payload)

    def test_missing_fields_returns_400(self):
        response = self.view(
            self._request("patch", data={"other": "x"}), project_uuid=PROJECT_UUID
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("non_field_errors", response.data)

    def test_empty_body_returns_400(self):
        response = self.view(
            self._request("patch", data={}), project_uuid=PROJECT_UUID
        )
        self.assertEqual(response.status_code, 400)

    def test_wrong_type_human_support(self):
        response = self.view(
            self._request("patch", data={"human_support": "not-a-bool"}),
            project_uuid=PROJECT_UUID,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("human_support", response.data)

    def test_wrong_type_prompt(self):
        response = self.view(
            self._request("patch", data={"human_support_prompt": False}),
            project_uuid=PROJECT_UUID,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("human_support_prompt", response.data)

    @patch(f"{NEXUS_CLIENT_PATH}.patch_human_support")
    def test_connection_error_returns_502(self, mock_nexus):
        mock_nexus.side_effect = ConnectionError("refused")

        response = self.view(
            self._request("patch", data={"human_support": True}),
            project_uuid=PROJECT_UUID,
        )
        self.assertEqual(response.status_code, 502)


# ---------------------------------------------------------------------------
# Cache integration (end-to-end through view)
# ---------------------------------------------------------------------------


class CacheIntegrationTests(ViewTestMixin, TestCase):

    @patch("chats.core.cache_utils.get_redis_connection")
    @patch(f"{NEXUS_CLIENT_PATH}.get_human_support")
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

    @patch("chats.core.cache_utils.get_redis_connection")
    @patch(f"{NEXUS_CLIENT_PATH}.patch_human_support")
    @patch(f"{NEXUS_CLIENT_PATH}.get_human_support")
    def test_patch_updates_cache_for_next_get(
        self, mock_get, mock_patch, mock_redis
    ):
        mock_redis.return_value = self.fake_redis
        mock_get.return_value = _make_fake_response()

        self.view(self._request(), project_uuid=PROJECT_UUID)

        updated = {"human_support": False, "human_support_prompt": "Changed"}
        mock_patch.return_value = _make_fake_response(json_data=updated)

        self.view(self._request("patch", data=updated), project_uuid=PROJECT_UUID)

        mock_get.reset_mock()
        response = self.view(self._request(), project_uuid=PROJECT_UUID)
        self.assertEqual(response.data, updated)
        mock_get.assert_not_called()

    @patch("chats.core.cache_utils.NEXUS_SETTINGS_CACHE_ENABLED", False)
    @patch(f"{NEXUS_CLIENT_PATH}.get_human_support")
    def test_cache_disabled_always_calls_nexus(self, mock_nexus):
        mock_nexus.return_value = _make_fake_response()

        self.view(self._request(), project_uuid=PROJECT_UUID)
        self.view(self._request(), project_uuid=PROJECT_UUID)

        self.assertEqual(mock_nexus.call_count, 2)
