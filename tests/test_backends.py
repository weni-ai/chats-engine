from types import SimpleNamespace
from unittest import mock

from django.test import SimpleTestCase, override_settings

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

    @mock.patch(
        "chats.apps.accounts.authentication.drf.backends.invalidate_cached_user"
    )
    @mock.patch(
        "chats.apps.accounts.authentication.drf.backends.check_module_permission"
    )
    @mock.patch("chats.apps.accounts.authentication.drf.backends.get_cached_user")
    def test_create_user_sanitises_username(
        self, mock_get_cached_user, mock_check_perm, mock_invalidate
    ):
        """create_user should use email from claims and handle cache properly."""
        # Arrange
        mock_get_cached_user.return_value = None

        dummy_user_model = mock.Mock()
        dummy_user_instance = SimpleNamespace(
            first_name="", last_name="", save=mock.Mock()
        )
        dummy_user_model.objects.create.return_value = dummy_user_instance

        # Act
        with mock.patch.object(sut, "User", dummy_user_model):
            backend = DummyBackend()
            backend.UserModel = dummy_user_model
            claims = {
                "email": "john@weni.io",
                "given_name": "John",
                "family_name": "Doe",
            }
            result = backend.create_user(claims)

            # Assert
            mock_get_cached_user.assert_called_once_with("john@weni.io")
            dummy_user_model.objects.create.assert_called_once_with(
                email="john@weni.io"
            )
            self.assertEqual(result.first_name, "John")
            self.assertEqual(result.last_name, "Doe")
            result.save.assert_called_once()
            mock_invalidate.assert_called_once_with("john@weni.io")
            mock_check_perm.assert_called_once_with(claims, dummy_user_instance)


class GetUserinfoTests(SimpleTestCase):
    @override_settings(OIDC_CACHE_TOKEN=False)
    @mock.patch.object(sut.OIDCAuthenticationBackend, "get_userinfo")
    def test_get_userinfo_without_cache(self, mock_super):
        mock_super.return_value = {"email": "a@example.com"}
        backend = DummyBackend()
        backend.cache_token = False
        result = backend.get_userinfo("token")
        self.assertEqual(result["email"], "a@example.com")
        mock_super.assert_called_once()

    @override_settings(
        OIDC_CACHE_TOKEN=True, OIDC_CACHE_TTL=60, OIDC_INTERNAL_TOKEN_CACHE_TTL=120
    )
    @mock.patch("chats.apps.accounts.authentication.drf.backends.get_redis_connection")
    def test_get_userinfo_cache_hit(self, mock_redis):
        import json

        redis = mock.Mock()
        redis.get.return_value = json.dumps({"email": "cached@example.com"}).encode()
        mock_redis.return_value = redis

        backend = DummyBackend()
        backend.cache_token = True
        backend.cache_ttl = 60
        backend.internal_token_cache_ttl = 120

        result = backend.get_userinfo("token")
        self.assertEqual(result["email"], "cached@example.com")
        redis.set.assert_not_called()

    @override_settings(
        OIDC_CACHE_TOKEN=True, OIDC_CACHE_TTL=60, OIDC_INTERNAL_TOKEN_CACHE_TTL=300
    )
    @mock.patch.object(sut.OIDCAuthenticationBackend, "get_userinfo")
    @mock.patch("chats.apps.accounts.authentication.drf.backends.get_redis_connection")
    def test_get_userinfo_cache_miss_sets_cache(self, mock_redis, mock_super):
        import json

        redis = mock.Mock()
        redis.get.return_value = None
        mock_redis.return_value = redis
        mock_super.return_value = {
            "email": "new@example.com",
            "can_communicate_internally": True,
        }

        backend = DummyBackend()
        backend.cache_token = True
        backend.cache_ttl = 60
        backend.internal_token_cache_ttl = 300

        result = backend.get_userinfo("token")
        self.assertEqual(result["email"], "new@example.com")
        redis.set.assert_called_once()
        args = redis.set.call_args[0]
        self.assertEqual(args[0], "token")
        self.assertEqual(json.loads(args[1])["email"], "new@example.com")
        self.assertEqual(args[2], 300)

    @override_settings(
        OIDC_CACHE_TOKEN=True, OIDC_CACHE_TTL=45, OIDC_INTERNAL_TOKEN_CACHE_TTL=300
    )
    @mock.patch.object(sut.OIDCAuthenticationBackend, "get_userinfo")
    @mock.patch("chats.apps.accounts.authentication.drf.backends.get_redis_connection")
    def test_get_userinfo_cache_miss_regular_ttl(self, mock_redis, mock_super):
        redis = mock.Mock()
        redis.get.return_value = None
        mock_redis.return_value = redis
        mock_super.return_value = {"email": "user@example.com"}

        backend = DummyBackend()
        backend.cache_token = True
        backend.cache_ttl = 45
        backend.internal_token_cache_ttl = 300

        backend.get_userinfo("token")
        self.assertEqual(redis.set.call_args[0][2], 45)


class GetOrCreateUserTests(SimpleTestCase):
    @mock.patch(
        "chats.apps.accounts.authentication.drf.backends.check_module_permission"
    )
    @mock.patch("chats.apps.accounts.authentication.drf.backends.get_cached_user")
    def test_returns_none_without_email(self, mock_cached, mock_check):
        backend = DummyBackend()
        backend.get_userinfo = mock.Mock(return_value={})
        self.assertIsNone(backend.get_or_create_user("t", "id", {}))
        mock_cached.assert_not_called()

    @mock.patch(
        "chats.apps.accounts.authentication.drf.backends.invalidate_cached_user"
    )
    @mock.patch(
        "chats.apps.accounts.authentication.drf.backends.check_module_permission"
    )
    @mock.patch("chats.apps.accounts.authentication.drf.backends.get_cached_user")
    def test_cached_user_updates_names(self, mock_cached, mock_check, mock_invalidate):
        user = SimpleNamespace(first_name="Old", last_name="Name", save=mock.Mock())
        mock_cached.return_value = user

        backend = DummyBackend()
        backend.get_userinfo = mock.Mock(
            return_value={
                "email": "u@example.com",
                "given_name": "New",
                "family_name": "Last",
            }
        )

        result = backend.get_or_create_user("t", "id", {})
        self.assertIs(result, user)
        self.assertEqual(user.first_name, "New")
        self.assertEqual(user.last_name, "Last")
        user.save.assert_called_once()
        mock_invalidate.assert_called_once_with("u@example.com")
        mock_check.assert_called_once()

    @mock.patch(
        "chats.apps.accounts.authentication.drf.backends.invalidate_cached_user"
    )
    @mock.patch(
        "chats.apps.accounts.authentication.drf.backends.check_module_permission"
    )
    @mock.patch("chats.apps.accounts.authentication.drf.backends.get_cached_user")
    def test_cached_user_no_update(self, mock_cached, mock_check, mock_invalidate):
        user = SimpleNamespace(first_name="Same", last_name="Name", save=mock.Mock())
        mock_cached.return_value = user

        backend = DummyBackend()
        backend.get_userinfo = mock.Mock(
            return_value={
                "email": "u@example.com",
                "given_name": "Same",
                "family_name": "Name",
            }
        )

        backend.get_or_create_user("t", "id", {})
        user.save.assert_not_called()
        mock_invalidate.assert_not_called()

    @mock.patch(
        "chats.apps.accounts.authentication.drf.backends.invalidate_cached_user"
    )
    @mock.patch(
        "chats.apps.accounts.authentication.drf.backends.check_module_permission"
    )
    @mock.patch("chats.apps.accounts.authentication.drf.backends.get_cached_user")
    def test_creates_user_when_not_cached(
        self, mock_cached, mock_check, mock_invalidate
    ):
        mock_cached.return_value = None
        user = SimpleNamespace(first_name="", last_name="", save=mock.Mock())
        user_model = mock.Mock()
        user_model.objects.get_or_create.return_value = (user, True)

        backend = DummyBackend()
        backend.UserModel = user_model
        backend.get_userinfo = mock.Mock(
            return_value={
                "email": "new@example.com",
                "given_name": "First",
                "family_name": "Last",
            }
        )

        result = backend.get_or_create_user("t", "id", {})
        self.assertIs(result, user)
        self.assertEqual(user.first_name, "First")
        self.assertEqual(user.last_name, "Last")
        user.save.assert_called_once()
        mock_invalidate.assert_called_once_with("new@example.com")
        mock_check.assert_called_once()


class VerifyClaimsTests(SimpleTestCase):
    @mock.patch.object(
        sut.OIDCAuthenticationBackend, "verify_claims", return_value=True
    )
    def test_verify_claims_delegates(self, mock_super):
        backend = DummyBackend()
        self.assertTrue(backend.verify_claims({"email": "a@example.com"}))
        mock_super.assert_called_once()
