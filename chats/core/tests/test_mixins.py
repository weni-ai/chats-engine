from django.test import TestCase
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from chats.core.mixins import LanguageViewMixin
from chats.apps.accounts.models import User


class LanguageViewMixinTests(TestCase):
    def test_get_language_when_headers_language_is_provided(self):
        factory = APIRequestFactory()
        django_request = factory.get("/", HTTP_ACCEPT_LANGUAGE="es")
        request = Request(django_request)
        mixin = LanguageViewMixin()
        mixin.request = request
        self.assertEqual(mixin.get_language(), "es")

    def test_get_language_when_user_language_is_provided(self):
        factory = APIRequestFactory()
        django_request = factory.get("/")
        request = Request(django_request)
        user = User.objects.create(language="es")
        request.user = user
        mixin = LanguageViewMixin()
        mixin.request = request
        self.assertEqual(mixin.get_language(), "es")

    def test_get_language_falls_back_to_en_when_anonymous_and_no_header(self):
        factory = APIRequestFactory()
        django_request = factory.get("/")
        request = Request(django_request)
        mixin = LanguageViewMixin()
        mixin.request = request

        self.assertEqual(mixin.get_language(), "en")

    def test_get_language_falls_back_to_en_when_authenticated_user_has_no_language(
        self,
    ):
        factory = APIRequestFactory()
        django_request = factory.get("/")
        request = Request(django_request)
        user = User.objects.create(email="agent@example.com", language="")
        request.user = user
        mixin = LanguageViewMixin()
        mixin.request = request

        self.assertEqual(mixin.get_language(), "en")

    def test_header_language_takes_precedence_over_user_language(self):
        factory = APIRequestFactory()
        django_request = factory.get("/", HTTP_ACCEPT_LANGUAGE="pt-br")
        request = Request(django_request)
        user = User.objects.create(email="agent2@example.com", language="es")
        request.user = user
        mixin = LanguageViewMixin()
        mixin.request = request

        self.assertEqual(mixin.get_language(), "pt-br")
