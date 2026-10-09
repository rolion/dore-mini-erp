from decimal import Decimal

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class ExpensePagination(PageNumberPagination):
    """Paginación estándar más `total_amount`: suma de los gastos vigentes del filtro, en todas las páginas."""

    page_size_query_param = 'page_size'
    max_page_size = 100
    total_amount: Decimal = Decimal('0.00')

    def get_paginated_response(self, data):
        response = super().get_paginated_response(data)
        return Response({**response.data, 'total_amount': f'{self.total_amount:.2f}'})


class CategoryPagination(PageNumberPagination):
    page_size_query_param = 'page_size'
    max_page_size = 100
