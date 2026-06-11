import operator
from functools import reduce

from django.db.models import Q
from rest_framework.filters import SearchFilter

from chats.apps.contacts.models import normalize_document
from chats.core.phone import ninth_digit_search_enabled_from_request, phone_urn_q


def build_field_search_q(
    field: str,
    term: str,
    construct_search,
    ninth_digit_enabled: bool = False,
) -> Q | None:
    if field.endswith("document"):
        value = normalize_document(term)
        return Q(**{construct_search(field): value}) if value else None
    if field.endswith("urn"):
        phone_q = phone_urn_q(term, field=field) if ninth_digit_enabled else None
        default_q = Q(**{construct_search(field): term})
        return phone_q | default_q if phone_q else default_q
    return Q(**{construct_search(field): term})


class PhoneAwareSearchFilter(SearchFilter):
    """
    DRF SearchFilter that expands URN lookups to match Brazilian mobile
    numbers with or without the 9th digit.
    """

    def filter_queryset(self, request, queryset, view):
        search_fields = self.get_search_fields(view, request)
        search_terms = self.get_search_terms(request)
        if not search_fields or not search_terms:
            return queryset

        ninth_digit_enabled = ninth_digit_search_enabled_from_request(request)
        conditions = []
        for term in search_terms:
            field_qs = []
            for field in map(str, search_fields):
                field_q = build_field_search_q(
                    field,
                    term,
                    self.construct_search,
                    ninth_digit_enabled=ninth_digit_enabled,
                )
                if field_q is not None:
                    field_qs.append(field_q)
            if not field_qs:
                return queryset.none()
            conditions.append(reduce(operator.or_, field_qs))

        queryset = queryset.filter(reduce(operator.and_, conditions))
        if self.must_call_distinct(queryset, search_fields):
            queryset = queryset.distinct()
        return queryset


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

        ninth_digit_enabled = ninth_digit_search_enabled_from_request(request)
        conditions = []
        for term in search_terms:
            field_qs = []
            for field in map(str, search_fields):
                field_q = build_field_search_q(
                    field,
                    term,
                    self.construct_search,
                    ninth_digit_enabled=ninth_digit_enabled,
                )
                if field_q is not None:
                    field_qs.append(field_q)
            if not field_qs:
                # The user supplied a term, but after per-field normalization
                # nothing remains to match against. Treat it as an explicit
                # "no results" instead of silently dropping the filter.
                return queryset.none()
            conditions.append(reduce(operator.or_, field_qs))

        queryset = queryset.filter(reduce(operator.and_, conditions))
        if self.must_call_distinct(queryset, search_fields):
            queryset = queryset.distinct()
        return queryset
