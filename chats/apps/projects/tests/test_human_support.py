import json
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from chats.apps.api.v1.projects.views_human_support import (
    HumanSupportNexusSettingsView,
)
from chats.apps.projects.models import Project, ProjectPermission
from chats.core import cache_utils

User = get_user_model()

PROJECT_UUID = "550e8400-e29b-41d4-a716-446655440000"
NEXUS_RESPONSE_DATA = {
    "human_support": True,
    "human_support_prompt": "Aguarde enquanto conectamos você com um atendente.",
}


def _make_fake_nexus_response(status_code=200, json_data=None):
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


class HumanSupportTestMixin:
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = HumanSupportNexusSettingsView.as_view()
        self.fake_redis = FakeRedis()

        self.project = Project.objects.create(
            uuid=PROJECT_UUID, name="Test Project", timezone="UTC"
        )
        self.user = User.objects.create_user(
            email="agent@test.com", password="x"
        )
        self.permission = ProjectPermission.objects.create(
            project=self.project,
            user=self.user,
            role=ProjectPermission.ROLE_ADMIN,
        )

        self.outsider = User.objects.create_user(
            email="outsider@test.com", password="x"
        )

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


class HumanSupportPermissionTests(HumanSupportTestMixin, TestCase):

    @patch(
        "chats.apps.api.v1.projects.views_human_support.get_nexus_settings_cached",
        return_value=NEXUS_RESPONSE_DATA,
    )
    def test_user_with_permission_can_get(self, _cache):
        request = self._request("get")
        response = self.view(request, project_uuid=PROJECT_UUID)
        self.assertEqual(response.status_code, 200)

    @patch(
        "chats.apps.api.v1.projects.views_human_support.get_nexus_settings_cached",
        return_value=NEXUS_RESPONSE_DATA,
    )
    def test_user_without_permission_gets_403(self, _cache):
        request = self._request("get", user=self.outsider)
        response = self.view(request, project_uuid=PROJECT_UUID)
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_gets_401(self):
        request = self.factory.get(f"/v1/project/{PROJECT_UUID}/human-support/")
        response = self.view(request, project_uuid=PROJECT_UUID)
        self.assertEqual(response.status_code, 401)

    @patch(
        "chats.apps.api.v1.internal.rest_clients.nexus_rest_client.NexusRESTClient.patch_human_support"
    )
    def test_outsider_cannot_patch(self, mock_nexus):
        mock_nexus.return_value = _make_fake_nexus_response()
        request = self._request("patch", data={"human_support": True}, user=self.outsider)
        response = self.view(request, project_uuid=PROJECT_UUID)
        self.assertEqual(response.status_code, 403)
        mock_nexus.assert_not_called()


class HumanSupportGetTests(HumanSupportTestMixin, TestCase):

    @patch("chats.apps.api.v1.projects.views_human_support.get_nexus_settings_cached")
    def test_get_returns_cached_data(self, mock_cache_get):
        mock_cache_get.return_value = NEXUS_RESPONSE_DATA

        request = self._request()
        response = self.view(request, project_uuid=PROJECT_UUID)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, NEXUS_RESPONSE_DATA)
        mock_cache_get.assert_called_once_with(PROJECT_UUID)

    @patch("chats.apps.api.v1.projects.views_human_support.set_nexus_settings_cache")
    @patch(
        "chats.apps.api.v1.internal.rest_clients.nexus_rest_client.NexusRESTClient.get_human_support"
    )
    @patch("chats.apps.api.v1.projects.views_human_support.get_nexus_settings_cached")
    def test_get_cache_miss_calls_nexus(
        self, mock_cache_get, mock_nexus_get, mock_cache_set
    ):
        mock_cache_get.return_value = None
        mock_nexus_get.return_value = _make_fake_nexus_response()

        request = self._request()
        response = self.view(request, project_uuid=PROJECT_UUID)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, NEXUS_RESPONSE_DATA)
        mock_nexus_get.assert_called_once_with(PROJECT_UUID)
        mock_cache_set.assert_called_once_with(PROJECT_UUID, NEXUS_RESPONSE_DATA)

    @patch(
        "chats.apps.api.v1.internal.rest_clients.nexus_rest_client.NexusRESTClient.get_human_support"
    )
    @patch("chats.apps.api.v1.projects.views_human_support.get_nexus_settings_cached")
    def test_get_nexus_error_forwards_status(self, mock_cache_get, mock_nexus_get):
        mock_cache_get.return_value = None
        error_data = {"error": "Project not found"}
        mock_nexus_get.return_value = _make_fake_nexus_response(
            status_code=404, json_data=error_data
        )

        request = self._request()
        response = self.view(request, project_uuid=PROJECT_UUID)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data, error_data)

    @patch(
        "chats.apps.api.v1.internal.rest_clients.nexus_rest_client.NexusRESTClient.get_human_support"
    )
    @patch("chats.apps.api.v1.projects.views_human_support.get_nexus_settings_cached")
    def test_get_nexus_connection_error_returns_502(
        self, mock_cache_get, mock_nexus_get
    ):
        mock_cache_get.return_value = None
        mock_nexus_get.side_effect = ConnectionError("Connection refused")

        request = self._request()
        response = self.view(request, project_uuid=PROJECT_UUID)

        self.assertEqual(response.status_code, 502)

    @patch(
        "chats.apps.api.v1.internal.rest_clients.nexus_rest_client.NexusRESTClient.get_human_support"
    )
    @patch("chats.core.cache_utils.get_redis_connection", side_effect=Exception("down"))
    def test_get_redis_down_falls_back_to_nexus(self, _, mock_nexus_get):
        mock_nexus_get.return_value = _make_fake_nexus_response()

        request = self._request()
        response = self.view(request, project_uuid=PROJECT_UUID)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, NEXUS_RESPONSE_DATA)

    @patch("chats.apps.api.v1.projects.views_human_support.set_nexus_settings_cache")
    @patch(
        "chats.apps.api.v1.internal.rest_clients.nexus_rest_client.NexusRESTClient.get_human_support"
    )
    @patch("chats.apps.api.v1.projects.views_human_support.get_nexus_settings_cached")
    def test_get_nexus_error_does_not_cache(
        self, mock_cache_get, mock_nexus_get, mock_cache_set
    ):
        mock_cache_get.return_value = None
        mock_nexus_get.return_value = _make_fake_nexus_response(
            status_code=500, json_data={"error": "Internal server error"}
        )

        request = self._request()
        response = self.view(request, project_uuid=PROJECT_UUID)

        self.assertEqual(response.status_code, 500)
        mock_cache_set.assert_not_called()


class HumanSupportPatchTests(HumanSupportTestMixin, TestCase):

    @patch("chats.apps.api.v1.projects.views_human_support.set_nexus_settings_cache")
    @patch(
        "chats.apps.api.v1.internal.rest_clients.nexus_rest_client.NexusRESTClient.patch_human_support"
    )
    def test_patch_success_updates_cache(self, mock_nexus_patch, mock_cache_set):
        updated = {"human_support": True, "human_support_prompt": "Updated prompt"}
        mock_nexus_patch.return_value = _make_fake_nexus_response(json_data=updated)

        request = self._request("patch", data=updated)
        response = self.view(request, project_uuid=PROJECT_UUID)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, updated)
        mock_nexus_patch.assert_called_once_with(PROJECT_UUID, updated)
        mock_cache_set.assert_called_once_with(PROJECT_UUID, updated)

    @patch(
        "chats.apps.api.v1.internal.rest_clients.nexus_rest_client.NexusRESTClient.patch_human_support"
    )
    def test_patch_only_human_support(self, mock_nexus_patch):
        payload = {"human_support": False}
        nexus_resp = {"human_support": False, "human_support_prompt": "existing"}
        mock_nexus_patch.return_value = _make_fake_nexus_response(json_data=nexus_resp)

        request = self._request("patch", data=payload)
        response = self.view(request, project_uuid=PROJECT_UUID)

        self.assertEqual(response.status_code, 200)
        mock_nexus_patch.assert_called_once_with(PROJECT_UUID, payload)

    @patch(
        "chats.apps.api.v1.internal.rest_clients.nexus_rest_client.NexusRESTClient.patch_human_support"
    )
    def test_patch_only_prompt(self, mock_nexus_patch):
        payload = {"human_support_prompt": "New prompt"}
        nexus_resp = {"human_support": True, "human_support_prompt": "New prompt"}
        mock_nexus_patch.return_value = _make_fake_nexus_response(json_data=nexus_resp)

        request = self._request("patch", data=payload)
        response = self.view(request, project_uuid=PROJECT_UUID)

        self.assertEqual(response.status_code, 200)
        mock_nexus_patch.assert_called_once_with(PROJECT_UUID, payload)

    def test_patch_missing_fields_returns_400(self):
        request = self._request("patch", data={"unrelated_field": "value"})
        response = self.view(request, project_uuid=PROJECT_UUID)

        self.assertEqual(response.status_code, 400)
        self.assertIn("At least one of", response.data["error"])

    def test_patch_empty_body_returns_400(self):
        request = self._request("patch", data={})
        response = self.view(request, project_uuid=PROJECT_UUID)
        self.assertEqual(response.status_code, 400)

    def test_patch_human_support_wrong_type_returns_400(self):
        request = self._request("patch", data={"human_support": "yes"})
        response = self.view(request, project_uuid=PROJECT_UUID)

        self.assertEqual(response.status_code, 400)
        self.assertIn("must be a boolean", response.data["error"])

    def test_patch_prompt_wrong_type_returns_400(self):
        request = self._request("patch", data={"human_support_prompt": 123})
        response = self.view(request, project_uuid=PROJECT_UUID)

        self.assertEqual(response.status_code, 400)
        self.assertIn("must be a string", response.data["error"])

    @patch("chats.apps.api.v1.projects.views_human_support.set_nexus_settings_cache")
    @patch(
        "chats.apps.api.v1.internal.rest_clients.nexus_rest_client.NexusRESTClient.patch_human_support"
    )
    def test_patch_nexus_error_does_not_update_cache(
        self, mock_nexus_patch, mock_cache_set
    ):
        mock_nexus_patch.return_value = _make_fake_nexus_response(
            status_code=400, json_data={"error": "Invalid data"}
        )

        request = self._request("patch", data={"human_support": True})
        response = self.view(request, project_uuid=PROJECT_UUID)

        self.assertEqual(response.status_code, 400)
        mock_cache_set.assert_not_called()

    @patch(
        "chats.apps.api.v1.internal.rest_clients.nexus_rest_client.NexusRESTClient.patch_human_support"
    )
    def test_patch_nexus_connection_error_returns_502(self, mock_nexus_patch):
        mock_nexus_patch.side_effect = ConnectionError("Connection refused")

        request = self._request("patch", data={"human_support": True})
        response = self.view(request, project_uuid=PROJECT_UUID)

        self.assertEqual(response.status_code, 502)


class HumanSupportCacheIntegrationTests(HumanSupportTestMixin, TestCase):

    @patch("chats.core.cache_utils.get_redis_connection")
    @patch(
        "chats.apps.api.v1.internal.rest_clients.nexus_rest_client.NexusRESTClient.get_human_support"
    )
    def test_get_populates_cache_then_serves_from_cache(
        self, mock_nexus_get, mock_redis_conn
    ):
        mock_redis_conn.return_value = self.fake_redis
        mock_nexus_get.return_value = _make_fake_nexus_response()

        request = self._request()
        response = self.view(request, project_uuid=PROJECT_UUID)
        self.assertEqual(response.status_code, 200)
        mock_nexus_get.assert_called_once()

        mock_nexus_get.reset_mock()
        request = self._request()
        response = self.view(request, project_uuid=PROJECT_UUID)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, NEXUS_RESPONSE_DATA)
        mock_nexus_get.assert_not_called()

    @patch("chats.core.cache_utils.get_redis_connection")
    @patch(
        "chats.apps.api.v1.internal.rest_clients.nexus_rest_client.NexusRESTClient.patch_human_support"
    )
    @patch(
        "chats.apps.api.v1.internal.rest_clients.nexus_rest_client.NexusRESTClient.get_human_support"
    )
    def test_patch_updates_cache_for_subsequent_gets(
        self, mock_nexus_get, mock_nexus_patch, mock_redis_conn
    ):
        mock_redis_conn.return_value = self.fake_redis
        mock_nexus_get.return_value = _make_fake_nexus_response()

        request = self._request()
        self.view(request, project_uuid=PROJECT_UUID)

        updated = {"human_support": False, "human_support_prompt": "Changed"}
        mock_nexus_patch.return_value = _make_fake_nexus_response(json_data=updated)

        request = self._request("patch", data=updated)
        response = self.view(request, project_uuid=PROJECT_UUID)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, updated)

        mock_nexus_get.reset_mock()
        request = self._request()
        response = self.view(request, project_uuid=PROJECT_UUID)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, updated)
        mock_nexus_get.assert_not_called()

    @patch("chats.core.cache_utils.NEXUS_SETTINGS_CACHE_ENABLED", False)
    @patch(
        "chats.apps.api.v1.internal.rest_clients.nexus_rest_client.NexusRESTClient.get_human_support"
    )
    def test_cache_disabled_always_calls_nexus(self, mock_nexus_get):
        mock_nexus_get.return_value = _make_fake_nexus_response()

        request = self._request()
        self.view(request, project_uuid=PROJECT_UUID)

        request = self._request()
        self.view(request, project_uuid=PROJECT_UUID)

        self.assertEqual(mock_nexus_get.call_count, 2)


class NexusSettingsCacheUtilsTests(TestCase):

    @patch("chats.core.cache_utils.get_redis_connection")
    def test_get_set_invalidate_cycle(self, mock_conn):
        r = FakeRedis()
        mock_conn.return_value = r

        self.assertIsNone(cache_utils.get_nexus_settings_cached(PROJECT_UUID))

        cache_utils.set_nexus_settings_cache(PROJECT_UUID, NEXUS_RESPONSE_DATA)

        cached = cache_utils.get_nexus_settings_cached(PROJECT_UUID)
        self.assertEqual(cached, NEXUS_RESPONSE_DATA)

        cache_utils.invalidate_nexus_settings_cache(PROJECT_UUID)
        self.assertIsNone(cache_utils.get_nexus_settings_cached(PROJECT_UUID))

    @patch("chats.core.cache_utils.NEXUS_SETTINGS_CACHE_ENABLED", False)
    def test_cache_disabled_returns_none(self):
        self.assertIsNone(cache_utils.get_nexus_settings_cached(PROJECT_UUID))

    @patch("chats.core.cache_utils.NEXUS_SETTINGS_CACHE_ENABLED", False)
    def test_set_cache_disabled_is_noop(self):
        cache_utils.set_nexus_settings_cache(PROJECT_UUID, NEXUS_RESPONSE_DATA)

    @patch("chats.core.cache_utils.NEXUS_SETTINGS_CACHE_ENABLED", False)
    def test_invalidate_cache_disabled_is_noop(self):
        cache_utils.invalidate_nexus_settings_cache(PROJECT_UUID)

    def test_empty_uuid_returns_none(self):
        self.assertIsNone(cache_utils.get_nexus_settings_cached(""))

    @patch("chats.core.cache_utils.get_redis_connection", side_effect=Exception("down"))
    def test_get_redis_down_returns_none(self, _):
        self.assertIsNone(cache_utils.get_nexus_settings_cached(PROJECT_UUID))

    @patch("chats.core.cache_utils.get_redis_connection", side_effect=Exception("down"))
    def test_invalidate_redis_down_is_silent(self, _):
        cache_utils.invalidate_nexus_settings_cache(PROJECT_UUID)
