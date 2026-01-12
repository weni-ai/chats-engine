from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from chats.apps.accounts.models import User
from chats.core.cache_utils import get_cached_user, invalidate_cached_user


class CacheFunctionUnitTest(TestCase):
    """
    Unit tests for cache functions (get_cached_user, invalidate_cached_user)
    Tests the core cache functionality in isolation
    """

    def setUp(self):
        """Setup test data"""
        self.test_email = "test.user@example.com"

        self.user = User.objects.create(
            email=self.test_email,
            first_name="Test",
            last_name="User",
            is_active=True,
        )

        invalidate_cached_user(self.test_email)

    def tearDown(self):
        """Clean up cache"""
        invalidate_cached_user(self.test_email)

    def _count_upper_queries(self, queries):
        """Count queries with UPPER(email)"""
        return sum(
            1
            for q in queries
            if "UPPER" in q["sql"]
            and "email" in q["sql"]
            and "accounts_user" in q["sql"]
        )

    def _count_user_queries(self, queries):
        """Count SELECT queries to accounts_user"""
        return sum(
            1 for q in queries if "accounts_user" in q["sql"] and "SELECT" in q["sql"]
        )

    def test_get_cached_user_first_call_no_upper_query(self):
        """Test that get_cached_user doesn't use UPPER query on first call"""
        invalidate_cached_user(self.test_email)

        with CaptureQueriesContext(connection) as context:
            user = get_cached_user(self.test_email)

        upper_queries = self._count_upper_queries(context.captured_queries)
        user_queries = self._count_user_queries(context.captured_queries)

        self.assertGreater(user_queries, 0, "First call should query database")
        self.assertEqual(upper_queries, 0, "Should NOT use UPPER(email)")
        self.assertEqual(user.email, self.test_email)

    def test_get_cached_user_subsequent_calls_no_queries(self):
        """Test that subsequent calls use cache (0 database queries)"""
        invalidate_cached_user(self.test_email)
        get_cached_user(self.test_email)

        for i in range(3):
            with CaptureQueriesContext(connection) as context:
                user = get_cached_user(self.test_email)

            user_queries = self._count_user_queries(context.captured_queries)

            self.assertEqual(user_queries, 0, f"Call {i+2} should use cache")
            self.assertEqual(user.email, self.test_email)

    def test_cache_stores_complete_user_object(self):
        """Test that cache stores all necessary user fields"""
        invalidate_cached_user(self.test_email)

        user = get_cached_user(self.test_email)

        self.assertEqual(user.id, self.user.id)
        self.assertEqual(user.email, self.test_email)
        self.assertEqual(user.first_name, "Test")
        self.assertEqual(user.last_name, "User")
        self.assertEqual(user.is_active, True)

    def test_cache_invalidation(self):
        """Test that invalidation works correctly"""
        invalidate_cached_user(self.test_email)
        get_cached_user(self.test_email)

        with CaptureQueriesContext(connection) as context:
            get_cached_user(self.test_email)
        self.assertEqual(self._count_user_queries(context.captured_queries), 0)

        invalidate_cached_user(self.test_email)

        with CaptureQueriesContext(connection) as context:
            user = get_cached_user(self.test_email)

        user_queries = self._count_user_queries(context.captured_queries)
        upper_queries = self._count_upper_queries(context.captured_queries)

        self.assertGreater(user_queries, 0, "Should query DB after invalidation")
        self.assertEqual(upper_queries, 0, "Should NOT use UPPER after invalidation")
        self.assertEqual(user.email, self.test_email)


class IntegrationTest(TestCase):
    """
    Integration tests using real HTTP endpoints
    Tests complete authentication flow and validates absence of UPPER queries
    """

    def setUp(self):
        """Setup user and authentication"""
        self.client = APIClient()
        self.test_email = "integration.test@example.com"

        self.user = User.objects.create(
            email=self.test_email,
            first_name="Integration",
            last_name="Test",
            is_active=True,
        )

        self.token = Token.objects.create(user=self.user)
        invalidate_cached_user(self.test_email)

    def tearDown(self):
        """Clean up"""
        invalidate_cached_user(self.test_email)

    def _count_upper_queries(self, queries):
        """Count UPPER(email) queries"""
        return sum(
            1
            for q in queries
            if "accounts_user" in q["sql"]
            and "UPPER" in q["sql"]
            and "email" in q["sql"]
        )

    def test_http_requests_no_upper_queries(self):
        """Test that HTTP requests don't generate UPPER(email) queries"""

        with CaptureQueriesContext(connection) as context:
            try:
                response = self.client.get(
                    "/v1/sector/", HTTP_AUTHORIZATION=f"Token {self.token.key}"
                )
                print(f"Response status: {response.status_code}")
            except Exception as e:
                print(f"Exception: {e}")

        upper_queries = self._count_upper_queries(context.captured_queries)

        token_queries = sum(
            1 for q in context.captured_queries if "authtoken_token" in q["sql"]
        )

        for i, query in enumerate(context.captured_queries, 1):
            if "authtoken_token" in query["sql"] or "accounts_user" in query["sql"]:
                print(f"\n  Query {i}:")
                print(f"    {query['sql'][:150]}...")

        self.assertGreater(
            len(context.captured_queries), 0, "❌ FALHA: Nenhuma query foi executada!"
        )
        self.assertGreater(
            token_queries, 0, "❌ FALHA: Autenticação não rodou (sem token lookup)!"
        )
        self.assertEqual(upper_queries, 0, "❌ FALHA: Queries UPPER foram geradas!")


class ComparisonTest(TestCase):
    """
    Comparison tests: Old implementation vs New optimized implementation
    Demonstrates elimination of UPPER(email) queries
    """

    def setUp(self):
        """Setup test data"""
        self.test_email = "comparison.test@example.com"

        self.user = User.objects.create(
            email=self.test_email,
            first_name="Comparison",
            last_name="Test",
            is_active=True,
        )

        invalidate_cached_user(self.test_email)

    def tearDown(self):
        """Clean up"""
        invalidate_cached_user(self.test_email)

    def _count_upper_queries(self, queries):
        """Count queries with UPPER(email)"""
        return sum(
            1
            for q in queries
            if "UPPER" in q["sql"]
            and "email" in q["sql"]
            and "accounts_user" in q["sql"]
        )

    def _count_user_queries(self, queries):
        """Count all SELECT queries to accounts_user"""
        return sum(
            1 for q in queries if "accounts_user" in q["sql"] and "SELECT" in q["sql"]
        )

    def test_old_implementation_uses_upper(self):
        """OLD: email__iexact generates UPPER(email) query"""

        with CaptureQueriesContext(connection) as context:
            user = User.objects.filter(email__iexact=self.test_email).first()

        upper_queries = self._count_upper_queries(context.captured_queries)

        self.assertIsNotNone(user)
        self.assertGreater(upper_queries, 0, "Old way MUST generate UPPER queries")

    def test_new_implementation_no_upper(self):
        """NEW: get_cached_user does NOT generate UPPER(email) query"""

        invalidate_cached_user(self.test_email)

        with CaptureQueriesContext(connection) as context:
            user = get_cached_user(self.test_email)

        upper_queries = self._count_upper_queries(context.captured_queries)

        self.assertIsNotNone(user)
        self.assertEqual(upper_queries, 0, "New way should NOT generate UPPER queries")

    def test_side_by_side_comparison(self):
        """Side-by-side comparison showing 100% elimination of UPPER queries"""

        with CaptureQueriesContext(connection) as old_context:
            old_user = User.objects.filter(email__iexact=self.test_email).first()

        old_upper = self._count_upper_queries(old_context.captured_queries)

        invalidate_cached_user(self.test_email)
        with CaptureQueriesContext(connection) as new_context:
            new_user = get_cached_user(self.test_email)

        new_upper = self._count_upper_queries(new_context.captured_queries)

        self.assertGreater(old_upper, new_upper)
        self.assertEqual(new_upper, 0)
        self.assertEqual(old_user.email, new_user.email)
