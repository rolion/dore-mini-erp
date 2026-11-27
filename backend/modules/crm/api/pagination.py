from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class CrmCustomerPagination(PageNumberPagination):
    page_size_query_param = 'page_size'
    max_page_size = 100
    meta: dict = {}

    def get_paginated_response(self, data):
        response = super().get_paginated_response(data)
        response.data['meta'] = self.meta
        return Response(response.data)


class CrmListPagination(PageNumberPagination):
    """Listados de prospectos y oportunidades: `page_size` hasta 200 (el Kanban carga las abiertas de un tablero)."""
    page_size_query_param = 'page_size'
    max_page_size = 200
