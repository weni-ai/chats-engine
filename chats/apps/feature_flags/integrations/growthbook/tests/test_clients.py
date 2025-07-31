from unittest.mock import call, patch
from django.test import TestCase

from chats.apps.feature_flags.integrations.growthbook.clients import GrowthbookClient
from chats.core.tests.mock import MockCacheClient


class TestGrowthbookClient(TestCase):
    def setUp(self):
        self.host_base_url = "https://growthbook.local"
        self.client: GrowthbookClient = GrowthbookClient(
            host_base_url=self.host_base_url,
            client_key="test",
            cache_client=MockCacheClient(),
            short_cache_key="growthbook:feature_flags:short",
            short_cache_ttl=60 * 60 * 24,
            long_cache_key="growthbook:feature_flags:long",
            long_cache_ttl=60 * 60 * 24 * 30,
        )

    @patch("chats.core.tests.mock.MockCacheClient.get")
    def test_get_feature_flags_from_short_cache(self, mock_get):
        mock_get.return_value = None

        flags = self.client.get_feature_flags_from_short_cache()

        self.assertIsNone(flags)

        mock_get.assert_called_once_with(self.client.short_cache_key)
        mock_get.reset_mock()

        example_feature_flags = {"test": True}
        mock_get.return_value = example_feature_flags

        flags = self.client.get_feature_flags_from_short_cache()

        self.assertEqual(flags, example_feature_flags)

        mock_get.assert_called_once_with(self.client.short_cache_key)

    @patch("chats.core.tests.mock.MockCacheClient.get")
    def test_get_feature_flags_from_long_cache(self, mock_get):
        mock_get.return_value = None

        flags = self.client.get_feature_flags_from_long_cache()

        self.assertIsNone(flags)

        mock_get.assert_called_once_with(self.client.long_cache_key)
        mock_get.reset_mock()

        example_feature_flags = {"test": True}
        mock_get.return_value = example_feature_flags

        flags = self.client.get_feature_flags_from_long_cache()

        self.assertEqual(flags, example_feature_flags)

        mock_get.assert_called_once_with(self.client.long_cache_key)

    @patch("chats.core.tests.mock.MockCacheClient.get")
    @patch(
        "chats.apps.feature_flags.integrations.growthbook.tasks.update_growthbook_feature_flags.delay"
    )
    def test_get_feature_flags_from_cache_when_cache_is_empty(
        self, mock_update_growthbook_feature_flags, mock_get
    ):
        mock_get.return_value = None

        flags = self.client.get_feature_flags_from_cache()

        self.assertIsNone(flags)

        mock_get.assert_has_calls(
            [
                call(self.client.short_cache_key),
                call(self.client.long_cache_key),
            ]
        )
        mock_update_growthbook_feature_flags.assert_called_once()

    @patch("chats.core.tests.mock.MockCacheClient.get")
    @patch(
        "chats.apps.feature_flags.integrations.growthbook.tasks.update_growthbook_feature_flags.delay"
    )
    def test_get_feature_flags_from_cache_when_short_cache_is_empty(
        self, mock_update_growthbook_feature_flags, mock_get
    ):
        mock_get.side_effect = [None, {"test": True}]

        flags = self.client.get_feature_flags_from_cache()

        self.assertEqual(flags, {"test": True})

        mock_get.assert_has_calls(
            [
                call(self.client.short_cache_key),
                call(self.client.long_cache_key),
            ]
        )
        mock_update_growthbook_feature_flags.assert_called_once()

    @patch("chats.core.tests.mock.MockCacheClient.get")
    @patch(
        "chats.apps.feature_flags.integrations.growthbook.tasks.update_growthbook_feature_flags.delay"
    )
    def test_get_feature_flags_from_cache_when_short_cache_is_valid(
        self, mock_update_growthbook_feature_flags, mock_get
    ):
        mock_get.side_effect = [{"test": True}, {"test": True}]

        flags = self.client.get_feature_flags_from_cache()

        self.assertEqual(flags, {"test": True})

        mock_get.assert_called_once_with(self.client.short_cache_key)
        mock_update_growthbook_feature_flags.assert_not_called()
