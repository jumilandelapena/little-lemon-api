from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    """``?page=2&perpage=5`` (default 10 per page, max 50)."""

    page_size = 10
    page_size_query_param = "perpage"
    max_page_size = 50
