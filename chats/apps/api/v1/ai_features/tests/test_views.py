from unittest.mock import MagicMock, patch

from django.conf import settings
from django.urls import reverse
from django.utils import translation
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APITestCase

from chats.apps.accounts.models import User
from chats.apps.ai_features.history_summary.enums import HistorySummaryFeedbackTags
from chats.apps.ai_features.improve_user_message.choices import (
    ImprovedUserMessageTypeChoices,
)
from chats.apps.feature_flags.exceptions import FeatureFlagInactiveError
from chats.apps.projects.models import Project
from chats.apps.projects.models.models import ProjectPermission


class BaseHistorySummaryFeedbackTagsViewTests(APITestCase):
    def get_history_summary_feedback_tags(self, language: str = None) -> Response:
        url = reverse("history_summary_feedback_tags")

        headers = {}
        if language:
            headers["HTTP_ACCEPT_LANGUAGE"] = language

        return self.client.get(url, **headers)


class TestHistorySummaryFeedbackTagsViewAsAnonymousUser(
    BaseHistorySummaryFeedbackTagsViewTests
):
    def test_get_history_summary_feedback_tags_without_authentication(self):
        response = self.get_history_summary_feedback_tags()
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestHistorySummaryFeedbackTagsViewAsAuthenticatedUser(
    BaseHistorySummaryFeedbackTagsViewTests
):
    def setUp(self):
        self.user = User.objects.create(email="test@test.com")
        self.client.force_authenticate(user=self.user)

    def test_get_history_summary_feedback_tags_without_specific_language(self):
        response = self.get_history_summary_feedback_tags()

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["results"]

        for tag in HistorySummaryFeedbackTags:
            translation.activate(settings.DEFAULT_LANGUAGE)
            self.assertEqual(results.get(tag.value), _(tag.label))

    def test_get_history_summary_feedback_tags_with_es_language_in_headers(self):
        response = self.get_history_summary_feedback_tags(language="es")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["results"]

        for tag in HistorySummaryFeedbackTags:
            translation.activate("es")
            self.assertEqual(results.get(tag.value), _(tag.label))

    def test_get_history_summary_feedback_tags_with_pt_BR_language_in_headers(self):
        response = self.get_history_summary_feedback_tags(language="pt-BR")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["results"]

        for tag in HistorySummaryFeedbackTags:
            translation.activate("pt-BR")
            self.assertEqual(results.get(tag.value), _(tag.label))

    def test_get_history_summary_feedback_tags_with_en_language_in_headers(self):
        response = self.get_history_summary_feedback_tags(language="en")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["results"]

        for tag in HistorySummaryFeedbackTags:
            translation.activate("en")
            self.assertEqual(results.get(tag.value), _(tag.label))

    def test_get_history_summary_feedback_tags_with_es_user_language(self):
        self.user.language = "es"
        self.user.save(update_fields=["language"])
        response = self.get_history_summary_feedback_tags()

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["results"]

        for tag in HistorySummaryFeedbackTags:
            translation.activate("es")
            self.assertEqual(results.get(tag.value), _(tag.label))

    def test_get_history_summary_feedback_tags_with_pt_BR_user_language(self):
        self.user.language = "pt-BR"
        self.user.save(update_fields=["language"])
        response = self.get_history_summary_feedback_tags()

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["results"]

        for tag in HistorySummaryFeedbackTags:
            translation.activate("pt-BR")
            self.assertEqual(results.get(tag.value), _(tag.label))

    def test_get_history_summary_feedback_tags_with_en_user_language(self):
        self.user.language = "en"
        self.user.save(update_fields=["language"])
        response = self.get_history_summary_feedback_tags()

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["results"]

        for tag in HistorySummaryFeedbackTags:
            translation.activate("en")
            self.assertEqual(results.get(tag.value), _(tag.label))


class TestAITextImprovementViewAsAnonymousUser(APITestCase):
    def test_returns_401_without_authentication(self):
        url = reverse("ai_text_improvement")
        response = self.client.post(
            url,
            {"text": "hello wrold", "type": "GRAMMAR_AND_SPELLING"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


@patch(
    "chats.apps.api.v1.ai_features.views.ImproveUserMessageUseCase"
)
class TestAITextImprovementViewAsAuthenticatedUser(APITestCase):
    def setUp(self):
        self.user = User.objects.create(email="test@test.com")
        self.client.force_authenticate(user=self.user)
        self.project = Project.objects.create(name="Test Project")
        ProjectPermission.objects.create(
            project=self.project,
            user=self.user,
            role=ProjectPermission.ROLE_ADMIN,
        )
        self.url = reverse("ai_text_improvement")

    def _post(self, data):
        return self.client.post(self.url, data, format="json")

    def test_returns_improved_text(self, mock_use_case_cls):
        mock_use_case_cls.return_value.execute.return_value = "hello world"

        response = self._post(
            {
                "text": "hello wrold",
                "type": "GRAMMAR_AND_SPELLING",
                "project_uuid": str(self.project.uuid),
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["text"], "hello world")

    def test_calls_use_case_with_correct_params(self, mock_use_case_cls):
        mock_use_case_cls.return_value.execute.return_value = "improved"

        self._post(
            {
                "text": "hello wrold",
                "type": "GRAMMAR_AND_SPELLING",
                "project_uuid": str(self.project.uuid),
            }
        )

        mock_use_case_cls.return_value.execute.assert_called_once_with(
            text="hello wrold",
            improvement_type="GRAMMAR_AND_SPELLING",
            project=self.project,
        )

    def test_returns_400_when_text_is_missing(self, _mock_use_case_cls):
        response = self._post(
            {
                "type": "GRAMMAR_AND_SPELLING",
                "project_uuid": str(self.project.uuid),
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_returns_400_when_type_is_missing(self, _mock_use_case_cls):
        response = self._post(
            {
                "text": "hello wrold",
                "project_uuid": str(self.project.uuid),
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_returns_400_when_project_uuid_is_missing(self, _mock_use_case_cls):
        response = self._post(
            {
                "text": "hello wrold",
                "type": "GRAMMAR_AND_SPELLING",
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_returns_400_for_invalid_type(self, _mock_use_case_cls):
        response = self._post(
            {
                "text": "hello wrold",
                "type": "INVALID_TYPE",
                "project_uuid": str(self.project.uuid),
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_returns_403_for_nonexistent_project(self, _mock_use_case_cls):
        response = self._post(
            {
                "text": "hello wrold",
                "type": "GRAMMAR_AND_SPELLING",
                "project_uuid": "00000000-0000-0000-0000-000000000000",
            }
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_returns_403_when_user_has_no_project_permission(self, _mock_use_case_cls):
        other_project = Project.objects.create(name="Other Project")
        response = self._post(
            {
                "text": "hello wrold",
                "type": "GRAMMAR_AND_SPELLING",
                "project_uuid": str(other_project.uuid),
            }
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_returns_403_when_feature_flag_is_inactive(self, mock_use_case_cls):
        mock_use_case_cls.return_value.execute.side_effect = FeatureFlagInactiveError()

        response = self._post(
            {
                "text": "hello wrold",
                "type": "GRAMMAR_AND_SPELLING",
                "project_uuid": str(self.project.uuid),
            }
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_returns_400_when_use_case_raises_value_error(self, mock_use_case_cls):
        mock_use_case_cls.return_value.execute.side_effect = ValueError("prompt error")

        response = self._post(
            {
                "text": "hello wrold",
                "type": "GRAMMAR_AND_SPELLING",
                "project_uuid": str(self.project.uuid),
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_accepts_all_valid_improvement_types(self, mock_use_case_cls):
        mock_use_case_cls.return_value.execute.return_value = "improved"

        for choice in ImprovedUserMessageTypeChoices:
            response = self._post(
                {
                    "text": "some text",
                    "type": choice.value,
                    "project_uuid": str(self.project.uuid),
                }
            )
            self.assertEqual(
                response.status_code,
                status.HTTP_200_OK,
                f"Failed for type {choice.value}",
            )
