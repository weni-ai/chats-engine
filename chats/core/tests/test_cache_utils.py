from unittest.mock import patch

from django.test import TestCase

from chats.apps.accounts.models import User
from chats.apps.projects.models import Project
from chats.core import cache_utils


class FakeRedis:
    def __init__(self):
        self.store = {}

    def get(self, k):
        return self.store.get(k)

    def setex(self, k, ttl, v):
        self.store[k] = str(v).encode() if isinstance(v, int) else v

    def delete(self, k):
        if k in self.store:
            del self.store[k]
        return 1


class GetUserIdByEmailCachedTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(email="agent@acme.com", first_name="A")
        self.email = "Agent@Acme.com"

    @patch("chats.core.cache_utils.get_redis_connection")
    def test_positive_cache_flow(self, mock_conn):
        r = FakeRedis()
        mock_conn.return_value = r
        uid = cache_utils.get_user_id_by_email_cached(self.email)
        self.assertEqual(uid, self.user.pk)
        self.assertEqual(
            cache_utils.get_user_id_by_email_cached(self.email), self.user.pk
        )
        self.assertEqual(
            r.get(f"user:email:{self.email.lower()}"), str(self.user.pk).encode()
        )

    @patch("chats.core.cache_utils.get_redis_connection")
    def test_negative_cache_flow(self, mock_conn):
        r = FakeRedis()
        mock_conn.return_value = r
        uid = cache_utils.get_user_id_by_email_cached("noone@acme.com")
        self.assertIsNone(uid)
        self.assertEqual(r.get("user:email:noone@acme.com"), b"-1")
        self.assertIsNone(cache_utils.get_user_id_by_email_cached("noone@acme.com"))

    @patch("chats.core.cache_utils.get_redis_connection", side_effect=Exception("down"))
    def test_redis_down_fallbacks_to_db(self, _):
        self.assertEqual(
            cache_utils.get_user_id_by_email_cached(self.email), self.user.pk
        )

    @patch("chats.core.cache_utils.EMAIL_LOOKUP_CACHE_ENABLED", False)
    def test_cache_disabled_queries_db(self):
        self.assertEqual(
            cache_utils.get_user_id_by_email_cached(self.email), self.user.pk
        )

    @patch("chats.core.cache_utils.EMAIL_LOOKUP_CACHE_ENABLED", False)
    def test_cache_disabled_user_not_found(self):
        self.assertIsNone(cache_utils.get_user_id_by_email_cached("notexist@acme.com"))

    def test_blank_email_returns_none(self):
        self.assertIsNone(cache_utils.get_user_id_by_email_cached(""))
        self.assertIsNone(cache_utils.get_user_id_by_email_cached(None))

    @patch("chats.core.cache_utils.get_redis_connection")
    def test_stale_cache_deleted_user(self, mock_conn):
        r = FakeRedis()
        mock_conn.return_value = r

        uid = cache_utils.get_user_id_by_email_cached(self.email)
        self.assertEqual(uid, self.user.pk)

        self.user.delete()

        uid2 = cache_utils.get_user_id_by_email_cached(self.email)
        self.assertIsNone(uid2)

    @patch("chats.core.cache_utils.get_redis_connection")
    def test_redis_connection_returns_none(self, mock_conn):
        mock_conn.return_value = None

        uid = cache_utils.get_user_id_by_email_cached(self.email)
        self.assertEqual(uid, self.user.pk)


class CacheInvalidationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(email="test@example.com", first_name="Test")

    @patch("chats.core.cache_utils.get_redis_connection")
    def test_invalidate_user_email_cache(self, mock_conn):
        r = FakeRedis()
        mock_conn.return_value = r

        cache_utils.get_user_id_by_email_cached("test@example.com")
        self.assertIsNotNone(r.get("user:email:test@example.com"))

        cache_utils.invalidate_user_email_cache("test@example.com")
        self.assertIsNone(r.get("user:email:test@example.com"))

    @patch("chats.core.cache_utils.get_redis_connection")
    def test_email_change_invalidates_cache(self, mock_conn):
        r = FakeRedis()
        mock_conn.return_value = r

        cache_utils.get_user_id_by_email_cached("test@example.com")
        self.assertIsNotNone(r.get("user:email:test@example.com"))

        with self.captureOnCommitCallbacks(execute=True):
            self.user.email = "newemail@example.com"
            self.user.save()

        self.assertIsNone(r.get("user:email:test@example.com"))

    @patch("chats.core.cache_utils.get_redis_connection")
    def test_user_deletion_invalidates_cache(self, mock_conn):
        r = FakeRedis()
        mock_conn.return_value = r

        cache_utils.get_user_id_by_email_cached("test@example.com")
        self.assertIsNotNone(r.get("user:email:test@example.com"))

        with self.captureOnCommitCallbacks(execute=True):
            self.user.delete()

        self.assertIsNone(r.get("user:email:test@example.com"))

    @patch("chats.core.cache_utils.EMAIL_LOOKUP_CACHE_ENABLED", False)
    def test_invalidation_with_cache_disabled(self):
        cache_utils.invalidate_user_email_cache("test@example.com")
        cache_utils.invalidate_user_cache_by_id(self.user.pk)


class ProjectCacheTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(
            name="Test Project",
            uuid="550e8400-e29b-41d4-a716-446655440000",
            timezone="America/Sao_Paulo",
            org="test-org",
        )

    @patch("chats.core.cache_utils.get_redis_connection")
    def test_project_uuid_cache(self, mock_conn):
        r = FakeRedis()
        mock_conn.return_value = r

        project_data = cache_utils.get_project_by_uuid_cached(str(self.project.uuid))
        self.assertEqual(project_data["name"], "Test Project")

        project_data = cache_utils.get_project_by_uuid_cached(str(self.project.uuid))
        self.assertEqual(project_data["name"], "Test Project")

    @patch("chats.core.cache_utils.get_redis_connection")
    def test_project_config_cache(self, mock_conn):
        r = FakeRedis()
        mock_conn.return_value = r

        self.project.config = {"test_key": "test_value"}
        self.project.save()

        config = cache_utils.get_project_config_cached(str(self.project.uuid))
        self.assertEqual(config["test_key"], "test_value")


class GetCachedUserTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            email="cached@test.com",
            first_name="Cached",
            last_name="User",
            is_staff=False,
            is_active=True,
            is_superuser=False,
        )
        self.email = "Cached@Test.com"

    @patch("chats.core.cache_utils.get_redis_connection")
    def test_cache_hit_returns_user(self, mock_conn):
        r = FakeRedis()
        mock_conn.return_value = r

        user = cache_utils.get_cached_user(self.email)
        self.assertEqual(user.id, self.user.id)
        self.assertEqual(user.email, self.user.email)

        user2 = cache_utils.get_cached_user(self.email)
        self.assertEqual(user2.id, self.user.id)

    @patch("chats.core.cache_utils.get_redis_connection")
    def test_negative_cache_returns_none(self, mock_conn):
        r = FakeRedis()
        mock_conn.return_value = r

        user = cache_utils.get_cached_user("nonexistent@test.com")
        self.assertIsNone(user)
        self.assertEqual(r.get("user:object:nonexistent@test.com"), b"-1")

        user2 = cache_utils.get_cached_user("nonexistent@test.com")
        self.assertIsNone(user2)

    @patch("chats.core.cache_utils.get_redis_connection", side_effect=Exception("down"))
    def test_redis_down_fallbacks_to_db(self, _):
        user = cache_utils.get_cached_user(self.email)
        self.assertEqual(user.id, self.user.id)

    @patch("chats.core.cache_utils.USER_OBJECT_CACHE_ENABLED", False)
    def test_cache_disabled_queries_db(self):
        user = cache_utils.get_cached_user(self.email)
        self.assertEqual(user.id, self.user.id)

    def test_blank_email_returns_none(self):
        self.assertIsNone(cache_utils.get_cached_user(""))
        self.assertIsNone(cache_utils.get_cached_user(None))

    @patch("chats.core.cache_utils.get_redis_connection")
    def test_invalid_cached_data_deleted(self, mock_conn):
        r = FakeRedis()
        mock_conn.return_value = r

        cache_key = "user:object:cached@test.com"
        r.store[cache_key] = b"invalid json"

        user = cache_utils.get_cached_user(self.email)
        self.assertEqual(user.id, self.user.id)

    @patch("chats.core.cache_utils.get_redis_connection")
    def test_cached_user_has_correct_fields(self, mock_conn):
        r = FakeRedis()
        mock_conn.return_value = r

        user = cache_utils.get_cached_user(self.email)
        self.assertEqual(user.first_name, "Cached")
        self.assertEqual(user.last_name, "User")
        self.assertFalse(user.is_staff)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_superuser)
