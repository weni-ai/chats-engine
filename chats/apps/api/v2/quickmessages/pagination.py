from rest_framework.pagination import CursorPagination


class QuickMessageCursorPagination(CursorPagination):
    page_size = 100
    page_size_query_param = "limit"
    max_page_size = 200
    ordering = "-created_on"
