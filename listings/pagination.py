from rest_framework.pagination import PageNumberPagination


class FlexiblePagination(PageNumberPagination):
    """10 per page by default; the site can ask for up to 100 with ?page_size=100."""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100
