from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.reporting.application import queries
from modules.reporting.domain.period import PeriodError
from modules.reporting.infrastructure.adapters import (
    CustomerNamesAdapter,
    ExpensesReaderAdapter,
    SalesReaderAdapter,
    SystemClock,
)

from . import serializers
from .params import parse_period_params


def _run(use_case, **kwargs):
    try:
        return use_case.execute(**kwargs)
    except PeriodError as exc:
        raise ValidationError(exc.errors) from exc


class _PeriodReportView(APIView):
    """Reporte de solo lectura que recibe un periodo (`period` o `date_from` + `date_to`)."""

    present = staticmethod(lambda result: result)

    def build(self):
        raise NotImplementedError

    def get(self, request):
        result = _run(self.build(), params=parse_period_params(request.query_params))
        return Response(self.present(result))


class DashboardView(_PeriodReportView):
    present = staticmethod(serializers.dashboard_data)

    def build(self):
        return queries.GetDashboardSummary(SalesReaderAdapter(), ExpensesReaderAdapter(), SystemClock())


class SalesReportView(_PeriodReportView):
    present = staticmethod(serializers.sales_data)

    def build(self):
        return queries.GetSalesReport(SalesReaderAdapter(), SystemClock())


class ExpensesReportView(_PeriodReportView):
    present = staticmethod(serializers.expenses_data)

    def build(self):
        return queries.GetExpenseReport(ExpensesReaderAdapter(), SystemClock())


class SalesByChannelView(_PeriodReportView):
    present = staticmethod(serializers.channels_data)

    def build(self):
        return queries.GetSalesByChannel(SalesReaderAdapter(), SystemClock())


class TopProductsView(_PeriodReportView):
    present = staticmethod(serializers.products_data)

    def build(self):
        return queries.GetTopProducts(SalesReaderAdapter(), SystemClock())


class TopCustomersView(_PeriodReportView):
    present = staticmethod(serializers.customers_data)

    def build(self):
        return queries.GetTopCustomers(SalesReaderAdapter(), CustomerNamesAdapter(), SystemClock())


class PendingView(APIView):
    """Estado actual de los pedidos pendientes; no recibe periodo."""

    def get(self, request):
        report = queries.GetPendingOrders(SalesReaderAdapter(), CustomerNamesAdapter()).execute()
        return Response(serializers.pending_data(report))
