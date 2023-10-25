from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from django.http import JsonResponse


class CustomPagination(LimitOffsetPagination):
    page_size = 10
    max_page_size = 100

    def get_paginated_response(self, data):
        objects_count = len(data)
        response_data = {
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
            "count": objects_count,
            "results": data,
        }
        return response_data
