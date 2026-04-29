import operator
from functools import reduce

from django.db.models import Q
from rest_framework.filters import SearchFilter

from chats.apps.contacts.models import normalize_document


class DocumentAwareSearchFilter(SearchFilter):
    """
    DRF SearchFilter with two extras on top of the default behavior:

    1. Comma in the search term acts as OR between groups
       (`?search=foo,bar` returns rows matching `foo` OR `bar`).
       Whitespace inside each group keeps DRF's default AND semantics
       (`?search=joao silva` still requires both terms to match).

    2. Terms applied against fields whose path ends with `document` are
       normalized (digits/letters only, uppercased) before the LIKE.
       Needed because `Contact.document` is stored normalized, so
       `?search=123-4` has to be normalized to `1234` to match.
    """

    def filter_queryset(self, request, queryset, view):
        search_fields = self.get_search_fields(view, request)
        raw = request.query_params.get(self.search_param, "").strip()
        if not raw or not search_fields:
            return queryset

        groups = [g.strip() for g in raw.split(",") if g.strip()]
        if not groups:
            return queryset

        group_clauses = []
        for group in groups:
            terms = self._split_terms(group)
            if not terms:
                continue

            and_clauses = []
            for term in terms:
                field_qs = []
                for field in map(str, search_fields):
                    value = (
                        normalize_document(term)
                        if field.endswith("document")
                        else term
                    )
                    if value:
                        field_qs.append(Q(**{self.construct_search(field): value}))
                if field_qs:
                    and_clauses.append(reduce(operator.or_, field_qs))

            if and_clauses:
                group_clauses.append(reduce(operator.and_, and_clauses))

        if not group_clauses:
            return queryset

        queryset = queryset.filter(reduce(operator.or_, group_clauses))
        if self.must_call_distinct(queryset, search_fields):
            queryset = queryset.distinct()
        return queryset

    @staticmethod
    def _split_terms(value):
        return value.replace("\x00", "").split()
