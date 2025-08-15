from django_filters import rest_framework as filters


class UUIDInFilter(filters.BaseInFilter, filters.UUIDFilter):
    """
    Filter to filter by a list of UUIDs.
    """
