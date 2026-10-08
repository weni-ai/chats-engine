import json
from unittest.mock import MagicMock, patch

from django.test import TestCase

from chats.apps.api.v1.multi_agents.service import MultiAgentsNexusService
from chats.core import cache_utils

PROJECT_UUID = "550e8400-e29b-41d4-a716-446655440000"
NEXUS_RESPONSE_DATA = {"multi_agents": True}

SERVICE_CACHE_GET = (
    "chats.apps.api.v1.multi_agents.service.get_nexus_multi_agents_cached"
)
SERVICE_CACHE_SET = (
    "chats.apps.api.v1.multi_agents.service.set_nexus_multi_agents_cache"
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


class GetMultiAgentsTests(TestCase):

    @patch(SERVICE_CACHE_GET, return_value=NEXUS_RESPONSE_DATA)
    def test_returns_cached_data(self, _cache_get):
        client = MagicMock()
        service = MultiAgentsNexusService(client=client)

        data, code = service.get_multi_agents(PROJECT_UUID)

        self.assertEqual(code, 200)
        self.assertEqual(data, NEXUS_RESPONSE_DATA)
        client.get_multi_agents.assert_not_called()

    @patch(SERVICE_CACHE_SET)
    @patch(SERVICE_CACHE_GET, return_value=None)
    def test_cache_miss_calls_nexus_and_caches(self, _cache_get, mock_cache_set):
        client = MagicMock()
        client.get_multi_agents.return_value = _make_fake_response()
        service = MultiAgentsNexusService(client=client)

        data, code = service.get_multi_agents(PROJECT_UUID)

        self.assertEqual(code, 200)
        self.assertEqual(data, NEXUS_RESPONSE_DATA)
        client.get_multi_agents.assert_called_once_with(PROJECT_UUID)
        mock_cache_set.assert_called_once_with(PROJECT_UUID, NEXUS_RESPONSE_DATA)

    @patch(SERVICE_CACHE_SET)
    @patch(SERVICE_CACHE_GET, return_value=None)
    def test_nexus_error_does_not_cache(self, _cache_get, mock_cache_set):
        client = MagicMock()
        error_data = {"error": "Internal server error"}
        client.get_multi_agents.return_value = _make_fake_response(
            status_code=500, json_data=error_data
        )
        service = MultiAgentsNexusService(client=client)

        data, code = service.get_multi_agents(PROJECT_UUID)

        self.assertEqual(code, 500)
        self.assertEqual(data, error_data)
        mock_cache_set.assert_not_called()

    @patch(SERVICE_CACHE_SET)
    @patch(SERVICE_CACHE_GET, return_value=None)
    def test_normalizes_truthy_value_to_bool(self, _cache_get, mock_cache_set):
        client = MagicMock()
        client.get_multi_agents.return_value = _make_fake_response(
            json_data={"multi_agents": 1}
        )
        service = MultiAgentsNexusService(client=client)

        data, code = service.get_multi_agents(PROJECT_UUID)

        self.assertEqual(code, 200)
        self.assertEqual(data, {"multi_agents": True})
        mock_cache_set.assert_called_once_with(PROJECT_UUID, {"multi_agents": True})

    @patch(SERVICE_CACHE_SET)
    @patch(SERVICE_CACHE_GET, return_value=None)
    def test_normalizes_missing_field_to_false(self, _cache_get, mock_cache_set):
        client = MagicMock()
        client.get_multi_agents.return_value = _make_fake_response(json_data={})
        service = MultiAgentsNexusService(client=client)

        data, code = service.get_multi_agents(PROJECT_UUID)

        self.assertEqual(code, 200)
        self.assertEqual(data, {"multi_agents": False})
        mock_cache_set.assert_called_once_with(PROJECT_UUID, {"multi_agents": False})


class CacheUtilsTests(TestCase):

    @patch("chats.core.cache_utils.get_redis_connection")
    def test_get_and_set_cycle(self, mock_conn):
        r = FakeRedis()
        mock_conn.return_value = r

        self.assertIsNone(cache_utils.get_nexus_multi_agents_cached(PROJECT_UUID))

        cache_utils.set_nexus_multi_agents_cache(PROJECT_UUID, NEXUS_RESPONSE_DATA)

        cached = cache_utils.get_nexus_multi_agents_cached(PROJECT_UUID)
        self.assertEqual(cached, NEXUS_RESPONSE_DATA)

    @patch("chats.core.cache_utils.NEXUS_MULTI_AGENTS_CACHE_ENABLED", False)
    def test_cache_disabled_returns_none(self):
        self.assertIsNone(cache_utils.get_nexus_multi_agents_cached(PROJECT_UUID))

    @patch("chats.core.cache_utils.NEXUS_MULTI_AGENTS_CACHE_ENABLED", False)
    def test_set_cache_disabled_is_noop(self):
        cache_utils.set_nexus_multi_agents_cache(PROJECT_UUID, NEXUS_RESPONSE_DATA)

    def test_empty_uuid_returns_none(self):
        self.assertIsNone(cache_utils.get_nexus_multi_agents_cached(""))

    @patch("chats.core.cache_utils.get_redis_connection", side_effect=Exception("down"))
    def test_get_redis_down_returns_none(self, _):
        self.assertIsNone(cache_utils.get_nexus_multi_agents_cached(PROJECT_UUID))
