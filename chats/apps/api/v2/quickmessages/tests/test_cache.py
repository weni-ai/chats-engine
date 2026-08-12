from unittest.mock import patch

from django.test import SimpleTestCase

from chats.apps.api.v2.quickmessages.cache import (
    get_list_cache_key,
    get_list_user_qm_cache_key,
    invalidate_personal_quick_messages_cache,
    invalidate_sector_quick_messages_cache,
)


class QuickMessagesCacheTests(SimpleTestCase):
    @patch("chats.apps.api.v2.quickmessages.cache.cache")
    def test_get_list_user_qm_cache_key_creates_initial_version(self, mock_cache):
        mock_cache.get.return_value = None

        key = get_list_user_qm_cache_key(user_id=10, cursor="c1", limit="20")

        self.assertEqual(key, "personal_qm:v2:u10:v1:c1:20")
        mock_cache.set.assert_called_once_with(
            "personal_qm_version:10", 1, timeout=None
        )

    @patch("chats.apps.api.v2.quickmessages.cache.cache")
    def test_get_list_cache_key_for_sector(self, mock_cache):
        mock_cache.get.return_value = 3

        key = get_list_cache_key(
            sector_uuid="sec-1",
            cursor="c1",
            limit="10",
        )

        self.assertEqual(key, "sector_qm:v2:sector:sec-1:v3:c1:10")

    @patch("chats.apps.api.v2.quickmessages.cache.cache")
    def test_get_list_cache_key_for_project_creates_version(self, mock_cache):
        mock_cache.get.return_value = None

        key = get_list_cache_key(
            project_uuid="proj-1",
            cursor="c2",
            limit="5",
        )

        self.assertEqual(key, "sector_qm:v2:project:proj-1:v1:c2:5")
        mock_cache.set.assert_called_once_with(
            "project_qm_version:proj-1", 1, timeout=None
        )

    @patch("chats.apps.api.v2.quickmessages.cache.cache")
    def test_invalidate_personal_quick_messages_cache_increments_version(
        self, mock_cache
    ):
        mock_cache.get.return_value = None

        invalidate_personal_quick_messages_cache(7)

        mock_cache.set.assert_called_once_with(
            "personal_qm_version:7", 1, timeout=None
        )

    @patch("chats.apps.api.v2.quickmessages.cache.cache")
    def test_invalidate_sector_quick_messages_cache_bumps_sector_and_project(
        self, mock_cache
    ):
        mock_cache.get.side_effect = [4, 9]

        invalidate_sector_quick_messages_cache("sec-1", "proj-1")

        self.assertEqual(
            mock_cache.set.call_args_list[0].args,
            ("sector_qm_version:sec-1", 5),
        )
        self.assertEqual(
            mock_cache.set.call_args_list[1].args,
            ("project_qm_version:proj-1", 10),
        )

    @patch("chats.apps.api.v2.quickmessages.cache.cache")
    def test_invalidate_personal_from_existing_version(self, mock_cache):
        mock_cache.get.return_value = 2

        invalidate_personal_quick_messages_cache(1)

        mock_cache.set.assert_called_once_with(
            "personal_qm_version:1", 3, timeout=None
        )