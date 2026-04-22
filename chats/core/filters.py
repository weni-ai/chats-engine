import operator
from functools import reduce

from django.db.models import Q
from rest_framework.filters import SearchFilter

from chats.apps.contacts.models import normalize_document


class DocumentAwareSearchFilter(SearchFilter):
    """
    Same as DRF's SearchFilter, but when the current search_field ends
    with `document`, the search term is normalized (punctuation removed,
    uppercased) before the LIKE.

    Needed because Contact.document is stored normalized (see model
    save()), so `?search=123-4` has to be normalized to `1234` to match.
    Other fields keep the raw term.
    """

    def filter_queryset(self, request, queryset, view):
        search_fields = self.get_search_fields(view, request)
        search_terms = self.get_search_terms(request)
        if not search_fields or not search_terms:
            return queryset

        conditions = []
        for term in search_terms:
            field_qs = []
            for field in map(str, search_fields):
                value = normalize_document(term) if field.endswith("document") else term
                if value:
                    field_qs.append(Q(**{self.construct_search(field): value}))
            if field_qs:
                conditions.append(reduce(operator.or_, field_qs))

        if not conditions:
            return queryset

        queryset = queryset.filter(reduce(operator.and_, conditions))
        if self.must_call_distinct(queryset, search_fields):
            queryset = queryset.distinct()
        return queryset
