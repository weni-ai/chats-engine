from django.http import QueryDict
from django.test import SimpleTestCase

from chats.apps.core.filters import get_filters_from_query_params


class GetFiltersFromQueryParamsTests(SimpleTestCase):
    def test_single_value_returns_string(self):
        query_params = QueryDict("project=abc&status=open")

        result = get_filters_from_query_params(query_params)

        self.assertEqual(result, {"project": "abc", "status": "open"})

    def test_repeated_key_returns_list(self):
        query_params = QueryDict("tag=a&tag=b&tag=c")

        result = get_filters_from_query_params(query_params)

        self.assertEqual(result, {"tag": ["a", "b", "c"]})

    def test_mixed_single_and_repeated_keys(self):
        query_params = QueryDict("project=xyz&tag=one&tag=two")

        result = get_filters_from_query_params(query_params)

        self.assertEqual(result["project"], "xyz")
        self.assertEqual(result["tag"], ["one", "two"])

    def test_empty_query_params(self):
        result = get_filters_from_query_params(QueryDict(""))

        self.assertEqual(result, {})
