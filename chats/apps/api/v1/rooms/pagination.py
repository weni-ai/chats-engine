from collections import OrderedDict

from django.conf import settings
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.utils.urls import replace_query_param


class RoomListPagination(LimitOffsetPagination):
    """
    Pagination class for the room list endpoint.

    It adds the max pin limit to the response.
    """

    def get_paginated_response(self, data):
        return Response(
            OrderedDict(
                [
                    ("max_pin_limit", settings.MAX_ROOM_PINS_LIMIT),
                    ("count", self.count),
                    ("next", self.get_next_link()),
                    ("previous", self.get_previous_link()),
                    ("results", data),
                ]
            )
        )

    def build_page_link(self, request, offset, limit, count):
        if offset >= count:
            return None
        url = self.get_base_url(request)
        return replace_query_param(
            replace_query_param(url, self.limit_query_param, limit),
            self.offset_query_param,
            offset,
        )

    def get_base_url(self, request):
        return request.build_absolute_uri()
