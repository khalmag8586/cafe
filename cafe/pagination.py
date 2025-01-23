from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from django.utils.translation import gettext_lazy as _

# class StandardResultsSetPagination(PageNumberPagination):
#     page_size = 5
#     page_size_query_param = "page_size"
#     max_page_size = 1000
#     page_query_param = "page"
#     def paginate_queryset(self, queryset, request, view=None):
#         try:
#             return super().paginate_queryset(queryset, request, view)
#         except Exception as e:
#             error_message = _("An error occurred while paginating the results.")
#             return Response({'error': error_message}, status=500)


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = "page_size"
    max_page_size = 1000

    def get_paginated_response(self, data):
        return Response(
            {
                "count": self.page.paginator.count,
                "num_pages": self.page.paginator.num_pages,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
            }
        )
