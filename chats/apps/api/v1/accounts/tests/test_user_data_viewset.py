from unittest.mock import patch

from django.test import RequestFactory, TestCase

from chats.apps.accounts.models import User
from chats.apps.api.v1.accounts.viewsets import UserDataViewset


class UserDataViewsetTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create(
            email="agent@acme.com", first_name="A", last_name="B"
        )

    @patch("chats.apps.api.v1.accounts.viewsets.get_user_id_by_email_cached")
    def test_retrieve_200(self, mock_cache):
        mock_cache.return_value = self.user.pk
        view = UserDataViewset.as_view({"get": "retrieve"})
        req = self.factory.get("/x?user_email=agent@acme.com")
        req.user = self.user
        resp = view(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["email"], "agent@acme.com")

    @patch(
        "chats.apps.api.v1.accounts.viewsets.get_user_id_by_email_cached",
        return_value=None,
    )
    def test_retrieve_404(self, _):
        view = UserDataViewset.as_view({"get": "retrieve"})
        req = self.factory.get("/x?user_email=not@acme.com")
        req.user = self.user
        resp = view(req)
        self.assertEqual(resp.status_code, 404)
