from collections import OrderedDict

from django.conf import settings
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response


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
