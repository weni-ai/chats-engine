from django.conf import settings
from rest_framework.settings import api_settings
from rest_framework.pagination import CursorPagination


class CustomCursorPagination(CursorPagination):
    page_size = api_settings.PAGE_SIZE
    page_size_query_param = "page_size"
    max_page_size = 100
    ordering = "-created_on"
