"""API del detalle de flujo de dinero (CONT-14): resumen por cuenta y movimientos. Solo lectura."""
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.accounting import services
from modules.accounting.application.cash_flow import CashFlowAccountNotFound
from shared import module_gate
from shared.tenancy import company_id_from

from .cash_flow_serializers import (
    CashFlowMovementsFiltersSerializer,
    CashFlowRangeSerializer,
    serialize_cash_flow,
    serialize_movement,
    serialize_movement_totals,
)


class CashFlowPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class CashFlowView(APIView):
    required_modules = ('accounting',)

    def get(self, request):
        serializer = CashFlowRangeSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        report = services.get_ledger_report(company_id_from(request), data['date_from'], data['date_to'])
        return Response({'period': {'date_from': data['date_from'], 'date_to': data['date_to']},
                         **serialize_cash_flow(report)})


class CashFlowMovementsView(APIView):
    required_modules = ('accounting',)

    def get(self, request):
        serializer = CashFlowMovementsFiltersSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        company_id = company_id_from(request)
        try:
            result = services.list_cash_flow_movements(company_id, data['date_from'], data['date_to'],
                                                       data.get('account_id'), data.get('type'))
        except CashFlowAccountNotFound as exc:
            raise ValidationError({'account_id': ['La cuenta no es una cuenta de dinero de esta empresa.']}) from exc
        enabled = module_gate.enabled_keys(company_id)
        paginator = CashFlowPagination()
        page = paginator.paginate_queryset(list(result.movements), request, view=self)
        response = paginator.get_paginated_response([serialize_movement(m, enabled) for m in page])
        response.data['totals'] = serialize_movement_totals(result)
        return response
