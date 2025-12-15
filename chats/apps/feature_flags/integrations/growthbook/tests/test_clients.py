import json
import uuid
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

        example_feature_flags = json.dumps({"test": True}, ensure_ascii=False)
        mock_get.return_value = example_feature_flags

        flags = self.client.get_feature_flags_from_short_cache()

        self.assertEqual(flags, json.loads(example_feature_flags))

        mock_get.assert_called_once_with(self.client.short_cache_key)

    @patch("chats.core.tests.mock.MockCacheClient.get")
    def test_get_feature_flags_from_long_cache(self, mock_get):
        mock_get.return_value = None

        flags = self.client.get_feature_flags_from_long_cache()

        self.assertIsNone(flags)

        mock_get.assert_called_once_with(self.client.long_cache_key)
        mock_get.reset_mock()

        example_feature_flags = json.dumps({"test": True}, ensure_ascii=False)
        mock_get.return_value = example_feature_flags

        flags = self.client.get_feature_flags_from_long_cache()

        self.assertEqual(flags, json.loads(example_feature_flags))

        mock_get.assert_called_once_with(self.client.long_cache_key)

    @patch("chats.core.tests.mock.MockCacheClient.get")
    def test_get_feature_flags_from_cache_when_cache_is_empty(self, mock_get):
        mock_get.return_value = None

        flags = self.client.get_feature_flags_from_cache()

        self.assertIsNone(flags)

        mock_get.assert_has_calls(
            [
                call(self.client.short_cache_key),
                call(self.client.long_cache_key),
            ]
        )

    @patch("chats.core.tests.mock.MockCacheClient.get")
    def test_get_feature_flags_from_cache_when_short_cache_is_empty(self, mock_get):
        mock_get.side_effect = [None, json.dumps({"test": True}, ensure_ascii=False)]

        flags = self.client.get_feature_flags_from_cache()

        self.assertEqual(flags, {"test": True})

        mock_get.assert_has_calls(
            [
                call(self.client.short_cache_key),
                call(self.client.long_cache_key),
            ]
        )

    @patch("chats.core.tests.mock.MockCacheClient.get")
    def test_get_feature_flags_from_cache_when_short_cache_is_valid(self, mock_get):
        mock_get.side_effect = [{"test": True}, {"test": True}]

        flags = self.client.get_feature_flags_from_cache()

        self.assertEqual(flags, {"test": True})

        mock_get.assert_called_once_with(self.client.short_cache_key)

    @patch("chats.core.tests.mock.MockCacheClient.set")
    def test_set_feature_flags_to_short_cache(self, mock_set):
        feature_flags = {"test": True}

        self.client.set_feature_flags_to_short_cache(feature_flags)
        mock_set.assert_called_once_with(
            self.client.short_cache_key,
            json.dumps(feature_flags, ensure_ascii=False),
            self.client.short_cache_ttl,
        )

    @patch("chats.core.tests.mock.MockCacheClient.set")
    def test_set_feature_flags_to_long_cache(self, mock_set):
        feature_flags = {"test": True}

        self.client.set_feature_flags_to_long_cache(feature_flags)
        mock_set.assert_called_once_with(
            self.client.long_cache_key,
            json.dumps(feature_flags, ensure_ascii=False),
            self.client.long_cache_ttl,
        )

    @patch("chats.core.tests.mock.MockCacheClient.delete")
    def test_flush_short_cache(self, mock_delete):
        self.client.flush_short_cache()

        mock_delete.assert_called_once_with(self.client.short_cache_key)

    @patch("chats.core.tests.mock.MockCacheClient.set")
    def test_set_feature_flags_to_cache(self, mock_set):
        feature_flags = {"test": True}

        self.client.set_feature_flags_to_cache(feature_flags)
        mock_set.assert_has_calls(
            [
                call(
                    self.client.short_cache_key,
                    json.dumps(feature_flags, ensure_ascii=False),
                    self.client.short_cache_ttl,
                ),
                call(
                    self.client.long_cache_key,
                    json.dumps(feature_flags, ensure_ascii=False),
                    self.client.long_cache_ttl,
                ),
            ]
        )

    @patch("chats.core.tests.mock.MockCacheClient.set")
    def test_update_feature_flags_definitions(self, mock_set):
        with patch("requests.get") as mock_get:
            mock_get.return_value.json.return_value = {
                "features": {"test": True},
            }

            self.client.update_feature_flags_definitions()

            mock_get.assert_called_once_with(
                f"{self.client.host_base_url}/api/features/{self.client.client_key}",
                timeout=60,
            )
            mock_set.assert_has_calls(
                [
                    call(
                        self.client.short_cache_key,
                        json.dumps({"test": True}, ensure_ascii=False),
                        self.client.short_cache_ttl,
                    ),
                    call(
                        self.client.long_cache_key,
                        json.dumps({"test": True}, ensure_ascii=False),
                        self.client.long_cache_ttl,
                    ),
                ]
            )

    @patch("chats.core.tests.mock.MockCacheClient.get")
    def test_get_feature_flags_when_cache_is_valid(self, mock_get):
        mock_get.side_effect = [{"test": True}, {"test": True}]

        flags = self.client.get_feature_flags()

        self.assertEqual(flags, {"test": True})
        mock_get.assert_called_once_with(self.client.short_cache_key)

    @patch("chats.core.tests.mock.MockCacheClient.get")
    @patch("chats.core.tests.mock.MockCacheClient.set")
    @patch("requests.get")
    def test_get_feature_flags_when_cache_is_invalid(
        self,
        mock_request_get,
        mock_cache_set,
        mock_cache_get,
    ):
        mock_request_get.return_value.json.return_value = {"features": {"test": True}}

        mock_cache_get.side_effect = [None, None]

        flags = self.client.get_feature_flags()

        self.assertEqual(flags, {"test": True})
        mock_cache_get.assert_has_calls(
            [call(self.client.short_cache_key), call(self.client.long_cache_key)]
        )
        mock_cache_set.assert_has_calls(
            [
                call(
                    self.client.short_cache_key,
                    json.dumps({"test": True}, ensure_ascii=False),
                    self.client.short_cache_ttl,
                ),
                call(
                    self.client.long_cache_key,
                    json.dumps({"test": True}, ensure_ascii=False),
                    self.client.long_cache_ttl,
                ),
            ]
        )
        mock_request_get.assert_called_once_with(
            f"{self.client.host_base_url}/api/features/{self.client.client_key}",
            timeout=60,
        )

    @patch(
        "chats.apps.feature_flags.integrations.growthbook.clients.GrowthbookClient.get_feature_flags"
    )
    def test_get_active_feature_flags_for_attributes(self, mock_get_feature_flags):
        attributes = {
            "userEmail": "test@vtex.com",
            "projectUUID": str(uuid.uuid4()),
        }

        mock_get_feature_flags.return_value = {
            # Always active while set to True in Growthbook
            "exampleWithoutRulesTrue": {
                "defaultValue": True,
                "rules": [],
            },
            # Always inactive while set to False in Growthbook
            "exampleWithoutRulesFalse": {
                "defaultValue": False,
                "rules": [],
            },
            # Active if project is in the list
            # It is expected to be active because the project is in the list
            # in the attributes above
            "exampleByProjectInTrue": {
                "defaultValue": False,
                "rules": [
                    {
                        "id": "fr_40644z1tmdqamcpe",
                        "condition": {
                            "projectUUID": {"$in": [attributes["projectUUID"]]}
                        },
                        "force": True,
                    }
                ],
            },
            # Active if project is not in the list
            # It is expected to be inactive because the project is not in the list
            # in the attributes above
            "exampleByProjectInFalse": {
                "defaultValue": False,
                "rules": [
                    {
                        "id": "fr_40644z1tmdrec3rs",
                        "condition": {"projectUUID": {"$in": [str(uuid.uuid4())]}},
                        "force": True,
                    }
                ],
            },
            # Active if project is not in the list
            # It is expected to be active because the project is not in the list
            # in the attributes above
            "exampleByProjectNotInTrue": {
                "defaultValue": False,
                "rules": [
                    {
                        "id": "fr_40644z1tmdrec3rs",
                        "condition": {"projectUUID": {"$nin": [str(uuid.uuid4())]}},
                        "force": True,
                    }
                ],
            },
            # Active if project is not in the list
            # It is expected to be inactive because the project is in the list
            # in the attributes above
            "exampleByProjectNotInFalse": {
                "defaultValue": False,
                "rules": [
                    {
                        "id": "fr_40644z1tmdrec3rs",
                        "condition": {
                            "projectUUID": {"$nin": [attributes["projectUUID"]]}
                        },
                        "force": True,
                    }
                ],
            },
            # Active if user email is the same as the one in the attributes
            # It is expected to be active because the user email is the same as the one in the attributes
            "exampleByEmailInTrue": {
                "defaultValue": False,
                "rules": [
                    {
                        "id": "fr_40644z1tmdrec3rs",
                        "condition": {"userEmail": {"$in": [attributes["userEmail"]]}},
                        "force": True,
                    }
                ],
            },
            # Active if user email is not the same as the one in the attributes
            # It is expected to be inactive because the user email is not the same as the one in the attributes
            "exampleByEmailInFalse": {
                "defaultValue": False,
                "rules": [
                    {
                        "id": "fr_40644z1tmdrec3rs",
                        "condition": {"userEmail": {"$in": ["other@test.com"]}},
                        "force": True,
                    }
                ],
            },
            # Active if user email domain is vtex.com
            # It is expected to be active because the user email domain is vtex.com
            "exampleByEmailInDomainTrue": {
                "defaultValue": False,
                "rules": [
                    {
                        "id": "fr_40644z1tmdrec3rs",
                        "condition": {
                            "userEmail": {
                                "$regex": "^[\\w.+-]+@([\\w-]+\\.)*vtex\\.com$"
                            }
                        },
                        "force": True,
                    },
                ],
            },
            # Active if user email domain is weni.ai
            # It is expected to be inactive because the user email domain is not weni.ai
            "exampleByEmailInDomainFalse": {
                "defaultValue": False,
                "rules": [
                    {
                        "id": "fr_40644z1tmdrec3rs",
                        "condition": {
                            "userEmail": {
                                "$regex": "^[\\w.+-]+@([\\w-]+\\.)*weni\\.ai$"
                            }
                        },
                        "force": True,
                    },
                ],
            },
        }

        features = self.client.get_active_feature_flags_for_attributes(attributes)

        self.assertEqual(
            features,
            [
                "exampleWithoutRulesTrue",
                "exampleByProjectInTrue",
                "exampleByProjectNotInTrue",
                "exampleByEmailInTrue",
                "exampleByEmailInDomainTrue",
            ],
        )

    @patch(
        "chats.apps.feature_flags.integrations.growthbook.clients.GrowthbookClient.get_feature_flags"
    )
    def test_evaluate_feature_flag_by_attributes(self, mock_get_feature_flags):
        attributes = {
            "projectUUID": str(uuid.uuid4()),
        }

        mock_get_feature_flags.return_value = {
            "example": {
                "defaultValue": False,
                "rules": [
                    {
                        "id": "fr_40644z1tmdrec3rs",
                        "condition": {
                            "projectUUID": {"$in": [attributes["projectUUID"]]}
                        },
                        "force": True,
                    }
                ],
            },
        }

        result = self.client.evaluate_feature_flag_by_attributes("example", attributes)

        self.assertTrue(result)
