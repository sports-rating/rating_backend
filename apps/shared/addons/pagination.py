from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class CustomPagination(PageNumberPagination):
    page_size = 10  # default number of items per page
    page_size_query_param = "page_size"  # query parameter for specifying page size
    max_page_size = 100  # maximum number of items per page

    def get_paginated_response(self, data):
        return Response(
            {
                "count": self.page.paginator.count,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "data": data,
            }
        )

    def get_page_size(self, request):
        """
        Get the page size from the query parameters.
        """
        page_size = request.query_params.get(self.page_size_query_param)
        if page_size:
            try:
                page_size = int(page_size)
                if page_size > 0:
                    return page_size
            except ValueError:
                pass
        return self.page_size
