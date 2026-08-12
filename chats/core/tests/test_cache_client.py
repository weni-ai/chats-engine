from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from chats.core.cache import CacheClient


class CacheClientTests(SimpleTestCase):
    @patch("chats.core.cache.get_redis_connection")
    def test_get_returns_value_from_redis(self, mock_get_redis):
        redis_connection = MagicMock()
        redis_connection.get.return_value = b"value"
        mock_get_redis.return_value.__enter__.return_value = redis_connection

        result = CacheClient().get("my-key")

        self.assertEqual(result, b"value")
        redis_connection.get.assert_called_once_with("my-key")

    @patch("chats.core.cache.get_redis_connection")
    def test_set_stores_value_with_expiration(self, mock_get_redis):
        redis_connection = MagicMock()
        redis_connection.set.return_value = True
        mock_get_redis.return_value.__enter__.return_value = redis_connection

        result = CacheClient().set("my-key", "payload", ex=60)

        self.assertTrue(result)
        redis_connection.set.assert_called_once_with("my-key", "payload", ex=60)

    @patch("chats.core.cache.get_redis_connection")
    def test_delete_removes_key(self, mock_get_redis):
        redis_connection = MagicMock()
        redis_connection.delete.return_value = 1
        mock_get_redis.return_value.__enter__.return_value = redis_connection

        result = CacheClient().delete("my-key")

        self.assertEqual(result, 1)
        redis_connection.delete.assert_called_once_with("my-key")
