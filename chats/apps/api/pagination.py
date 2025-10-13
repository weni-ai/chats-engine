from rest_framework.settings import api_settings
from rest_framework.pagination import CursorPagination, PageNumberPagination
from rest_framework.response import Response
from collections import OrderedDict


class CustomCursorPagination(CursorPagination):
    page_size = api_settings.PAGE_SIZE
    page_size_query_param = "page_size"
    max_page_size = 100
    ordering = "-created_on"


class PageNumberWithoutCountPagination(PageNumberPagination):
    page_size = api_settings.PAGE_SIZE
    page_size_query_param = "page_size"
    max_page_size = 100
    ordering = "-created_on"

    def get_paginated_response(self, data):
        return Response(
            OrderedDict(
                [
                    ("next", self.get_next_link()),
                    ("previous", self.get_previous_link()),
                    ("results", data),
                ]
            )
        )
