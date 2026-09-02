from collections import OrderedDict

from django.conf import settings
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response


class RoomListPagination(LimitOffsetPagination):
    """
    Pagination class for the room list endpoint.

    It adds the max pin limit to the response.
    """

    def configure(self, request, count):
        """Bind request, combined count, limit, and offset for link generation."""
        self.request = request
        self.count = count
        self.limit = self.get_limit(request)
        self.offset = self.get_offset(request)
        if self.limit is None:
            return None
        return self.limit, self.offset

    def get_paginated_response(self, data, pinned_rooms=None):
        payload = OrderedDict(
            [
                ("max_pin_limit", settings.MAX_ROOM_PINS_LIMIT),
                ("count", self.count),
                ("next", self.get_next_link()),
                ("previous", self.get_previous_link()),
                ("results", data),
            ]
        )
        if pinned_rooms is not None:
            payload["pinned_rooms"] = pinned_rooms
        return Response(payload)
