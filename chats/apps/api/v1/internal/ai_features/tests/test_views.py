import hmac
import json
import time

from django.urls import reverse
from django.test import override_settings
from rest_framework.test import APITestCase
from rest_framework.response import Response
from rest_framework import status

from chats.apps.ai_features.models import FeaturePrompt


class BaseFeaturePromptsViewTests(APITestCase):
    def setUp(self):
        FeaturePrompt.objects.create(
            feature="example",
            model="example",
            settings={"test": "test"},
            prompt="Test Prompt",
            version=1,
        )

    def get_feature_prompts(self) -> Response:
        url = reverse("ai_features_prompts")

        return self.client.get(url)

    def create_feature_prompt(self, data: dict) -> Response:
        url = reverse("ai_features_prompts")

        return self.client.post(url, data, format="json")


class FeaturePromptsViewTests(BaseFeaturePromptsViewTests):
    def test_get_feature_prompts_without_authentication(self):
        response = self.get_feature_prompts()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(AI_FEATURES_PROMPTS_API_SECRET="test_secret")
    def test_get_feature_prompts_with_authentication(self):
        timestamp = str(int(time.time()))
        signature = hmac.new(
            bytes("test_secret", "utf-8"), bytes(timestamp, "utf-8"), "sha256"
        ).hexdigest()

        self.client.credentials(
            HTTP_X_WENI_SIGNATURE=signature, HTTP_X_TIMESTAMP=timestamp
        )

        response = self.get_feature_prompts()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["feature"], "example")

    @override_settings(AI_FEATURES_PROMPTS_API_SECRET="test_secret")
    def test_get_feature_prompts_with_invalid_signature(self):
        timestamp = str(int(time.time()))
        signature = hmac.new(
            bytes("test_secret", "utf-8"), bytes("invalid", "utf-8"), "sha256"
        ).hexdigest()

        self.client.credentials(
            HTTP_X_WENI_SIGNATURE=signature, HTTP_X_TIMESTAMP=timestamp
        )

        response = self.get_feature_prompts()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_feature_prompt_without_authentication(self):
        response = self.create_feature_prompt(
            {
                "feature": "example",
                "model": "example",
                "settings": {"test": "test"},
                "prompt": "Test Prompt",
                "version": 1,
            }
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(AI_FEATURES_PROMPTS_API_SECRET="test_secret")
    def test_create_feature_prompt_with_authentication(self):
        body = {
            "feature": "example",
            "model": "example",
            "settings": {"test": "test"},
            "prompt": "Test Prompt",
            "version": 2,
        }

        timestamp = str(int(time.time()))

        message = json.dumps(body, separators=(",", ":")) + timestamp

        signature = hmac.new(
            bytes("test_secret", "utf-8"), bytes(message, "utf-8"), "sha256"
        ).hexdigest()

        self.client.credentials(
            HTTP_X_WENI_SIGNATURE=signature, HTTP_X_TIMESTAMP=timestamp
        )

        response = self.create_feature_prompt(body)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["feature"], "example")

    @override_settings(AI_FEATURES_PROMPTS_API_SECRET="test_secret")
    def test_create_feature_prompt_with_invalid_signature(self):
        body = {
            "feature": "example",
            "model": "example",
            "settings": {"test": "test"},
            "prompt": "Test Prompt",
            "version": 2,
        }

        timestamp = str(int(time.time()))

        signature = hmac.new(
            bytes("test_secret", "utf-8"), bytes("invalid", "utf-8"), "sha256"
        ).hexdigest()

        self.client.credentials(
            HTTP_X_WENI_SIGNATURE=signature, HTTP_X_TIMESTAMP=timestamp
        )

        response = self.create_feature_prompt(body)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(AI_FEATURES_PROMPTS_API_SECRET="test_secret")
    def test_create_feature_prompt_with_existing_version(self):
        body = {
            "feature": "example",
            "model": "example",
            "settings": {"test": "test"},
            "prompt": "Test Prompt",
            "version": 1,
        }

        timestamp = str(int(time.time()))

        message = json.dumps(body, separators=(",", ":")) + timestamp

        signature = hmac.new(
            bytes("test_secret", "utf-8"), bytes(message, "utf-8"), "sha256"
        ).hexdigest()

        self.client.credentials(
            HTTP_X_WENI_SIGNATURE=signature, HTTP_X_TIMESTAMP=timestamp
        )

        response = self.create_feature_prompt(body)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["non_field_errors"][0].code, "unique")
