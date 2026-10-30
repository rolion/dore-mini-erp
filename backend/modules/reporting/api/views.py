from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.reporting.application import queries
from modules.reporting.domain.period import PeriodError
from modules.reporting.infrastructure.adapters import (
    CustomerNamesAdapter,
    ExpensesReaderAdapter,
    SalesReaderAdapter,
    SourceAvailabilityAdapter,
    SystemClock,
)

from shared.tenancy import company_id_from

from . import serializers
from .params import parse_period_params


def _run(use_case, **kwargs):
    try:
        return use_case.execute(**kwargs)
    except PeriodError as exc:
        raise ValidationError(exc.errors) from exc


class _CompanyReportView(APIView):
    """Reporte de solo lectura de la empresa del usuario autenticado (nunca de un dato enviado por el cliente)."""

    required_modules = ('reporting',)

    def _company_id(self):
        return company_id_from(self.request)


class _PeriodReportView(_CompanyReportView):
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
        return queries.GetDashboardSummary(SalesReaderAdapter(self._company_id()), ExpensesReaderAdapter(self._company_id()),
                                           SourceAvailabilityAdapter(self._company_id()), SystemClock())


class SalesReportView(_PeriodReportView):
    required_modules = ('reporting', 'sales')
    present = staticmethod(serializers.sales_data)

    def build(self):
        return queries.GetSalesReport(SalesReaderAdapter(self._company_id()), SystemClock())


class ExpensesReportView(_PeriodReportView):
    required_modules = ('reporting', 'expenses')
    present = staticmethod(serializers.expenses_data)

    def build(self):
        return queries.GetExpenseReport(ExpensesReaderAdapter(self._company_id()), SystemClock())


class SalesByChannelView(_PeriodReportView):
    required_modules = ('reporting', 'sales')
    present = staticmethod(serializers.channels_data)

    def build(self):
        return queries.GetSalesByChannel(SalesReaderAdapter(self._company_id()), SystemClock())


class TopProductsView(_PeriodReportView):
    required_modules = ('reporting', 'sales')
    present = staticmethod(serializers.products_data)

    def build(self):
        return queries.GetTopProducts(SalesReaderAdapter(self._company_id()), SystemClock())


class TopCustomersView(_PeriodReportView):
    required_modules = ('reporting', 'sales', 'customers')
    present = staticmethod(serializers.customers_data)

    def build(self):
        return queries.GetTopCustomers(SalesReaderAdapter(self._company_id()), CustomerNamesAdapter(self._company_id()), SystemClock())


class PendingView(_CompanyReportView):
    """Estado actual de los pedidos pendientes; no recibe periodo."""

    required_modules = ('reporting', 'sales')

    def get(self, request):
        report = queries.GetPendingOrders(SalesReaderAdapter(self._company_id()), CustomerNamesAdapter(self._company_id())).execute()
        return Response(serializers.pending_data(report))
