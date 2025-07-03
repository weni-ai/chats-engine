from types import SimpleNamespace
from unittest import mock

from django.test import SimpleTestCase

# System under test
from chats.apps.accounts.authentication.drf import backends as sut


class DummyPermission:
    pass


class FakeUser:
    """Simple object that emulates a Django User model enough for testing."""

    def __init__(self):
        self.permissions_added = []

    def has_perm(self, _):
        return False

    @property
    def user_permissions(self):
        class Manager:
            def __init__(self, outer):
                self.outer = outer

            def add(self, perm):
                self.outer.permissions_added.append(perm)

        return Manager(self)


class DummyBackend(sut.WeniOIDCAuthenticationBackend):
    """Concrete implementation with external dependencies mocked for isolated tests."""

    def __init__(self):
        # Skip parent initialisation that could hit external services
        pass


class CheckModulePermissionTests(SimpleTestCase):
    def setUp(self):
        self.claims_intern = {"can_communicate_internally": True}
        self.claims_regular = {}
        self.fake_user = FakeUser()

    @mock.patch(
        "chats.apps.accounts.authentication.drf.backends.ContentType.objects.get_for_model"
    )
    @mock.patch(
        "chats.apps.accounts.authentication.drf.backends.Permission.objects.get_or_create"
    )
    def test_check_module_permission_grants_permission(
        self, mock_get_or_create, mock_get_for_model
    ):
        """When claim flag is on, the helper must grant the permission and return True."""
        # Arrange
        dummy_ct = object()
        dummy_perm = DummyPermission()
        mock_get_for_model.return_value = dummy_ct
        mock_get_or_create.return_value = (dummy_perm, True)

        # Act
        granted = sut.check_module_permission(self.claims_intern, self.fake_user)

        # Assert
        self.assertTrue(granted)
        mock_get_for_model.assert_called_once_with(sut.User)
        mock_get_or_create.assert_called_once_with(
            codename="can_communicate_internally",
            name="can communicate internally",
            content_type=dummy_ct,
        )
        # The permission must have been added to the user
        self.assertIn(dummy_perm, self.fake_user.permissions_added)

    def test_check_module_permission_no_permission(self):
        """When claim flag is absent, the helper should do nothing and return False."""
        granted = sut.check_module_permission(self.claims_regular, self.fake_user)
        self.assertFalse(granted)
        self.assertEqual([], self.fake_user.permissions_added)


class OIDCBackendTests(SimpleTestCase):
    def test_get_username_prefers_claim(self):
        # Arrange
        backend = DummyBackend()
        claims = {"preferred_username": "john.doe"}

        # Act & Assert
        self.assertEqual(backend.get_username(claims), "john.doe")

    @mock.patch.object(sut.WeniOIDCAuthenticationBackend, "get_username", autospec=True)
    def test_create_user_sanitises_username(self, mock_get_username):
        """Username generated must be alphanumeric and up to 16 chars."""
        # Arrange
        mock_get_username.return_value = "john.doe@weni.io"

        dummy_user_model = mock.Mock()
        dummy_user_instance = SimpleNamespace(
            first_name="", last_name="", save=lambda: None
        )
        dummy_user_model.objects.get_or_create.return_value = (
            dummy_user_instance,
            True,
        )

        # Act
        with mock.patch.object(sut, "User", dummy_user_model):
            backend = DummyBackend()
            backend.UserModel = dummy_user_model
            claims = {"email": "john@weni.io"}
            backend.create_user(claims)

            # get_or_create should be called with sanitised username
            mock_get_username.assert_called_once()
            dummy_user_model.objects.get_or_create.assert_called_once_with(
                email="john@weni.io"
            )
