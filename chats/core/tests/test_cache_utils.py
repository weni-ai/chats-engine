# chats/core/tests/test_cache_utils.py
from django.test import TestCase
from unittest.mock import patch, Mock
from chats.core import cache_utils
from chats.apps.accounts.models import User

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
        # hit cache
        self.assertEqual(cache_utils.get_user_id_by_email_cached(self.email), self.user.pk)
        # ensure cached value is present
        self.assertEqual(r.get(f"user:email:{self.email.lower()}"), str(self.user.pk).encode())

    @patch("chats.core.cache_utils.get_redis_connection")
    def test_negative_cache_flow(self, mock_conn):
        r = FakeRedis()
        mock_conn.return_value = r
        uid = cache_utils.get_user_id_by_email_cached("noone@acme.com")
        self.assertIsNone(uid)
        self.assertEqual(r.get("user:email:noone@acme.com"), b"-1")
        # hit negative cache
        self.assertIsNone(cache_utils.get_user_id_by_email_cached("noone@acme.com"))

    @patch("chats.core.cache_utils.get_redis_connection", side_effect=Exception("down"))
    def test_redis_down_fallbacks_to_db(self, _):
        self.assertEqual(cache_utils.get_user_id_by_email_cached(self.email), self.user.pk)

    @patch("chats.core.cache_utils.EMAIL_LOOKUP_CACHE_ENABLED", False)
    def test_cache_disabled_queries_db(self):
        self.assertEqual(cache_utils.get_user_id_by_email_cached(self.email), self.user.pk)

    def test_blank_email_returns_none(self):
        self.assertIsNone(cache_utils.get_user_id_by_email_cached(""))
        self.assertIsNone(cache_utils.get_user_id_by_email_cached(None))

class CacheInvalidationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(email="test@example.com", first_name="Test")
        
    @patch("chats.core.cache_utils.get_redis_connection")
    def test_invalidate_user_email_cache(self, mock_conn):
        r = FakeRedis()
        mock_conn.return_value = r
        
        # First, cache the user
        cache_utils.get_user_id_by_email_cached("test@example.com")
        self.assertIsNotNone(r.get("user:email:test@example.com"))
        
        # Invalidate the cache
        cache_utils.invalidate_user_email_cache("test@example.com")
        self.assertIsNone(r.get("user:email:test@example.com"))
    
    @patch("chats.core.cache_utils.get_redis_connection")
    def test_email_change_invalidates_cache(self, mock_conn):
        r = FakeRedis()
        mock_conn.return_value = r
        
        # Cache the original email
        cache_utils.get_user_id_by_email_cached("test@example.com")
        self.assertIsNotNone(r.get("user:email:test@example.com"))
        
        # Change the email
        self.user.email = "newemail@example.com"
        self.user.save()
        
        # Old email should be invalidated
        self.assertIsNone(r.get("user:email:test@example.com"))
        
    @patch("chats.core.cache_utils.get_redis_connection")
    def test_user_deletion_invalidates_cache(self, mock_conn):
        r = FakeRedis()
        mock_conn.return_value = r
        
        # Cache the user
        cache_utils.get_user_id_by_email_cached("test@example.com")
        self.assertIsNotNone(r.get("user:email:test@example.com"))
        
        # Delete the user
        self.user.delete()
        
        # Cache should be invalidated
        self.assertIsNone(r.get("user:email:test@example.com"))
    
    @patch("chats.core.cache_utils.EMAIL_LOOKUP_CACHE_ENABLED", False)
    def test_invalidation_with_cache_disabled(self):
        # Should not raise any errors
        cache_utils.invalidate_user_email_cache("test@example.com")
        cache_utils.invalidate_user_cache_by_id(self.user.pk)