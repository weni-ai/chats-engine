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
