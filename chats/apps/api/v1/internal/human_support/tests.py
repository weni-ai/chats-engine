import json
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from rest_framework.test import APIRequestFactory

from chats.apps.api.v1.internal.human_support.views import HumanSupportView
from chats.core import cache_utils


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


PROJECT_UUID = "550e8400-e29b-41d4-a716-446655440000"
NEXUS_RESPONSE_DATA = {
    "human_support": True,
    "human_support_prompt": "Aguarde enquanto conectamos você com um atendente.",
}
AUTH_TOKEN = "Bearer test-internal-token"


def _make_fake_nexus_response(status_code=200, json_data=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or NEXUS_RESPONSE_DATA
    resp.text = json.dumps(json_data or NEXUS_RESPONSE_DATA)
    return resp


class HumanSupportViewTestMixin:
    """Shared setup for human support view tests."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = HumanSupportView.as_view()
        self.fake_redis = FakeRedis()

    def _get_request(self, method="get", data=None):
        if method == "get":
            request = self.factory.get(
                f"/v1/internal/human-support/{PROJECT_UUID}/",
                HTTP_AUTHORIZATION=AUTH_TOKEN,
            )
        else:
            request = self.factory.patch(
                f"/v1/internal/human-support/{PROJECT_UUID}/",
                data=json.dumps(data) if data else None,
                content_type="application/json",
                HTTP_AUTHORIZATION=AUTH_TOKEN,
            )
        return request


@override_settings(INTERNAL_API_TOKEN="test-internal-token")
class HumanSupportGetTests(HumanSupportViewTestMixin, TestCase):

    @patch("chats.apps.api.v1.internal.human_support.views.get_human_support_cached")
    def test_get_returns_cached_data(self, mock_cache_get):
        mock_cache_get.return_value = NEXUS_RESPONSE_DATA

        request = self._get_request()
        response = self.view(request, project_uuid=PROJECT_UUID)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, NEXUS_RESPONSE_DATA)
        mock_cache_get.assert_called_once_with(PROJECT_UUID)

    @patch("chats.apps.api.v1.internal.human_support.views.set_human_support_cache")
    @patch(
        "chats.apps.api.v1.internal.rest_clients.nexus_rest_client.NexusRESTClient.get_human_support"
    )
    @patch("chats.apps.api.v1.internal.human_support.views.get_human_support_cached")
    def test_get_cache_miss_calls_nexus(
        self, mock_cache_get, mock_nexus_get, mock_cache_set
    ):
        mock_cache_get.return_value = None
        mock_nexus_get.return_value = _make_fake_nexus_response()

        request = self._get_request()
        response = self.view(request, project_uuid=PROJECT_UUID)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, NEXUS_RESPONSE_DATA)
        mock_nexus_get.assert_called_once_with(PROJECT_UUID)
        mock_cache_set.assert_called_once_with(PROJECT_UUID, NEXUS_RESPONSE_DATA)

    @patch(
        "chats.apps.api.v1.internal.rest_clients.nexus_rest_client.NexusRESTClient.get_human_support"
    )
    @patch("chats.apps.api.v1.internal.human_support.views.get_human_support_cached")
    def test_get_nexus_error_forwards_status(self, mock_cache_get, mock_nexus_get):
        mock_cache_get.return_value = None
        error_data = {"error": "Project with uuid `abc` does not exist"}
        mock_nexus_get.return_value = _make_fake_nexus_response(
            status_code=404, json_data=error_data
        )

        request = self._get_request()
        response = self.view(request, project_uuid=PROJECT_UUID)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data, error_data)

    @patch(
        "chats.apps.api.v1.internal.rest_clients.nexus_rest_client.NexusRESTClient.get_human_support"
    )
    @patch("chats.apps.api.v1.internal.human_support.views.get_human_support_cached")
    def test_get_nexus_connection_error_returns_502(
        self, mock_cache_get, mock_nexus_get
    ):
        mock_cache_get.return_value = None
        mock_nexus_get.side_effect = ConnectionError("Connection refused")

        request = self._get_request()
        response = self.view(request, project_uuid=PROJECT_UUID)

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.data["error"], "Failed to reach NEXUS API")

    @patch(
        "chats.apps.api.v1.internal.rest_clients.nexus_rest_client.NexusRESTClient.get_human_support"
    )
    @patch("chats.core.cache_utils.get_redis_connection", side_effect=Exception("down"))
    def test_get_redis_down_falls_back_to_nexus(self, _, mock_nexus_get):
        mock_nexus_get.return_value = _make_fake_nexus_response()

        request = self._get_request()
        response = self.view(request, project_uuid=PROJECT_UUID)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, NEXUS_RESPONSE_DATA)

    @patch("chats.apps.api.v1.internal.human_support.views.set_human_support_cache")
    @patch(
        "chats.apps.api.v1.internal.rest_clients.nexus_rest_client.NexusRESTClient.get_human_support"
    )
    @patch("chats.apps.api.v1.internal.human_support.views.get_human_support_cached")
    def test_get_nexus_error_does_not_cache(
        self, mock_cache_get, mock_nexus_get, mock_cache_set
    ):
        mock_cache_get.return_value = None
        mock_nexus_get.return_value = _make_fake_nexus_response(
            status_code=500, json_data={"error": "Internal server error"}
        )

        request = self._get_request()
        response = self.view(request, project_uuid=PROJECT_UUID)

        self.assertEqual(response.status_code, 500)
        mock_cache_set.assert_not_called()


@override_settings(INTERNAL_API_TOKEN="test-internal-token")
class HumanSupportPatchTests(HumanSupportViewTestMixin, TestCase):

    @patch("chats.apps.api.v1.internal.human_support.views.set_human_support_cache")
    @patch(
        "chats.apps.api.v1.internal.rest_clients.nexus_rest_client.NexusRESTClient.patch_human_support"
    )
    def test_patch_success_updates_cache(self, mock_nexus_patch, mock_cache_set):
        updated = {"human_support": True, "human_support_prompt": "Updated prompt"}
        mock_nexus_patch.return_value = _make_fake_nexus_response(
            json_data=updated
        )

        request = self._get_request("patch", data=updated)
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
        nexus_resp = {"human_support": False, "human_support_prompt": "existing prompt"}
        mock_nexus_patch.return_value = _make_fake_nexus_response(
            json_data=nexus_resp
        )

        request = self._get_request("patch", data=payload)
        response = self.view(request, project_uuid=PROJECT_UUID)

        self.assertEqual(response.status_code, 200)
        mock_nexus_patch.assert_called_once_with(PROJECT_UUID, payload)

    @patch(
        "chats.apps.api.v1.internal.rest_clients.nexus_rest_client.NexusRESTClient.patch_human_support"
    )
    def test_patch_only_prompt(self, mock_nexus_patch):
        payload = {"human_support_prompt": "New prompt"}
        nexus_resp = {"human_support": True, "human_support_prompt": "New prompt"}
        mock_nexus_patch.return_value = _make_fake_nexus_response(
            json_data=nexus_resp
        )

        request = self._get_request("patch", data=payload)
        response = self.view(request, project_uuid=PROJECT_UUID)

        self.assertEqual(response.status_code, 200)
        mock_nexus_patch.assert_called_once_with(PROJECT_UUID, payload)

    def test_patch_missing_fields_returns_400(self):
        request = self._get_request("patch", data={"unrelated_field": "value"})
        response = self.view(request, project_uuid=PROJECT_UUID)

        self.assertEqual(response.status_code, 400)
        self.assertIn("At least one of", response.data["error"])

    def test_patch_empty_body_returns_400(self):
        request = self._get_request("patch", data={})
        response = self.view(request, project_uuid=PROJECT_UUID)

        self.assertEqual(response.status_code, 400)

    def test_patch_human_support_wrong_type_returns_400(self):
        request = self._get_request("patch", data={"human_support": "yes"})
        response = self.view(request, project_uuid=PROJECT_UUID)

        self.assertEqual(response.status_code, 400)
        self.assertIn("must be a boolean", response.data["error"])

    def test_patch_prompt_wrong_type_returns_400(self):
        request = self._get_request("patch", data={"human_support_prompt": 123})
        response = self.view(request, project_uuid=PROJECT_UUID)

        self.assertEqual(response.status_code, 400)
        self.assertIn("must be a string", response.data["error"])

    @patch("chats.apps.api.v1.internal.human_support.views.set_human_support_cache")
    @patch(
        "chats.apps.api.v1.internal.rest_clients.nexus_rest_client.NexusRESTClient.patch_human_support"
    )
    def test_patch_nexus_error_does_not_update_cache(
        self, mock_nexus_patch, mock_cache_set
    ):
        mock_nexus_patch.return_value = _make_fake_nexus_response(
            status_code=400,
            json_data={"error": "Invalid data"},
        )

        request = self._get_request("patch", data={"human_support": True})
        response = self.view(request, project_uuid=PROJECT_UUID)

        self.assertEqual(response.status_code, 400)
        mock_cache_set.assert_not_called()

    @patch(
        "chats.apps.api.v1.internal.rest_clients.nexus_rest_client.NexusRESTClient.patch_human_support"
    )
    def test_patch_nexus_connection_error_returns_502(self, mock_nexus_patch):
        mock_nexus_patch.side_effect = ConnectionError("Connection refused")

        request = self._get_request("patch", data={"human_support": True})
        response = self.view(request, project_uuid=PROJECT_UUID)

        self.assertEqual(response.status_code, 502)


@override_settings(INTERNAL_API_TOKEN="test-internal-token")
class HumanSupportCacheIntegrationTests(HumanSupportViewTestMixin, TestCase):

    @patch("chats.core.cache_utils.get_redis_connection")
    @patch(
        "chats.apps.api.v1.internal.rest_clients.nexus_rest_client.NexusRESTClient.get_human_support"
    )
    def test_get_populates_cache_then_serves_from_cache(
        self, mock_nexus_get, mock_redis_conn
    ):
        mock_redis_conn.return_value = self.fake_redis
        mock_nexus_get.return_value = _make_fake_nexus_response()

        request = self._get_request()
        response = self.view(request, project_uuid=PROJECT_UUID)
        self.assertEqual(response.status_code, 200)
        mock_nexus_get.assert_called_once()

        mock_nexus_get.reset_mock()
        request = self._get_request()
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

        request = self._get_request()
        self.view(request, project_uuid=PROJECT_UUID)

        updated = {"human_support": False, "human_support_prompt": "Changed prompt"}
        mock_nexus_patch.return_value = _make_fake_nexus_response(json_data=updated)

        request = self._get_request("patch", data=updated)
        response = self.view(request, project_uuid=PROJECT_UUID)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, updated)

        mock_nexus_get.reset_mock()
        request = self._get_request()
        response = self.view(request, project_uuid=PROJECT_UUID)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, updated)
        mock_nexus_get.assert_not_called()

    @patch("chats.core.cache_utils.HUMAN_SUPPORT_CACHE_ENABLED", False)
    @patch(
        "chats.apps.api.v1.internal.rest_clients.nexus_rest_client.NexusRESTClient.get_human_support"
    )
    def test_cache_disabled_always_calls_nexus(self, mock_nexus_get):
        mock_nexus_get.return_value = _make_fake_nexus_response()

        request = self._get_request()
        self.view(request, project_uuid=PROJECT_UUID)

        request = self._get_request()
        self.view(request, project_uuid=PROJECT_UUID)

        self.assertEqual(mock_nexus_get.call_count, 2)


class HumanSupportCacheUtilsTests(TestCase):

    @patch("chats.core.cache_utils.get_redis_connection")
    def test_get_set_invalidate_cycle(self, mock_conn):
        r = FakeRedis()
        mock_conn.return_value = r

        self.assertIsNone(cache_utils.get_human_support_cached(PROJECT_UUID))

        cache_utils.set_human_support_cache(PROJECT_UUID, NEXUS_RESPONSE_DATA)

        cached = cache_utils.get_human_support_cached(PROJECT_UUID)
        self.assertEqual(cached, NEXUS_RESPONSE_DATA)

        cache_utils.invalidate_human_support_cache(PROJECT_UUID)
        self.assertIsNone(cache_utils.get_human_support_cached(PROJECT_UUID))

    @patch("chats.core.cache_utils.HUMAN_SUPPORT_CACHE_ENABLED", False)
    def test_cache_disabled_returns_none(self):
        self.assertIsNone(cache_utils.get_human_support_cached(PROJECT_UUID))

    @patch("chats.core.cache_utils.HUMAN_SUPPORT_CACHE_ENABLED", False)
    def test_set_cache_disabled_is_noop(self):
        cache_utils.set_human_support_cache(PROJECT_UUID, NEXUS_RESPONSE_DATA)

    @patch("chats.core.cache_utils.HUMAN_SUPPORT_CACHE_ENABLED", False)
    def test_invalidate_cache_disabled_is_noop(self):
        cache_utils.invalidate_human_support_cache(PROJECT_UUID)

    def test_empty_uuid_returns_none(self):
        self.assertIsNone(cache_utils.get_human_support_cached(""))

    @patch("chats.core.cache_utils.get_redis_connection", side_effect=Exception("down"))
    def test_get_redis_down_returns_none(self, _):
        self.assertIsNone(cache_utils.get_human_support_cached(PROJECT_UUID))

    @patch("chats.core.cache_utils.get_redis_connection", side_effect=Exception("down"))
    def test_invalidate_redis_down_is_silent(self, _):
        cache_utils.invalidate_human_support_cache(PROJECT_UUID)


class NexusRESTClientTests(TestCase):

    @override_settings(NEXUS_API_URL="https://nexus.example.com")
    @patch(
        "chats.apps.api.v1.internal.rest_clients.nexus_rest_client.get_request_session_with_retries"
    )
    def test_get_human_support(self, mock_session_factory):
        mock_session = MagicMock()
        mock_session.get.return_value = _make_fake_nexus_response()
        mock_session_factory.return_value = mock_session

        from chats.apps.api.v1.internal.rest_clients.nexus_rest_client import (
            NexusRESTClient,
        )

        client = NexusRESTClient(auth_token="Bearer my-token")
        response = client.get_human_support(PROJECT_UUID)

        self.assertEqual(response.status_code, 200)
        mock_session.get.assert_called_once_with(
            url=f"https://nexus.example.com/api/{PROJECT_UUID}/human-support",
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Authorization": "Bearer my-token",
            },
            timeout=10,
        )

    @override_settings(NEXUS_API_URL="https://nexus.example.com/")
    @patch(
        "chats.apps.api.v1.internal.rest_clients.nexus_rest_client.get_request_session_with_retries"
    )
    def test_trailing_slash_stripped(self, mock_session_factory):
        mock_session = MagicMock()
        mock_session.patch.return_value = _make_fake_nexus_response()
        mock_session_factory.return_value = mock_session

        from chats.apps.api.v1.internal.rest_clients.nexus_rest_client import (
            NexusRESTClient,
        )

        client = NexusRESTClient(auth_token="Bearer my-token")
        payload = {"human_support": True}
        client.patch_human_support(PROJECT_UUID, payload)

        mock_session.patch.assert_called_once_with(
            url=f"https://nexus.example.com/api/{PROJECT_UUID}/human-support",
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Authorization": "Bearer my-token",
            },
            json=payload,
            timeout=10,
        )
