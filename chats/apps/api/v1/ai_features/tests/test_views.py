from django.conf import settings
from django.urls import reverse
from django.utils import translation
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APITestCase

from chats.apps.accounts.models import User
from chats.apps.ai_features.history_summary.enums import HistorySummaryFeedbackTags


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
