"""API del reporte de ingresos y egresos por mes: solo lectura sobre el libro de asientos."""
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.accounting.application.income_expense import GetIncomeExpense
from modules.accounting.domain.account import AccountValidationError
from modules.accounting.infrastructure.django.repositories import DjangoFiscalPeriodRepository, DjangoJournalRepository
from shared.tenancy import company_id_from

from .income_expense_serializers import IncomeExpenseFiltersSerializer, serialize_income_expense


class IncomeExpenseView(APIView):
    required_modules = ('accounting',)

    def get(self, request):
        company_id = company_id_from(request)
        serializer = IncomeExpenseFiltersSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        use_case = GetIncomeExpense(DjangoFiscalPeriodRepository(company_id), DjangoJournalRepository(company_id))
        try:
            report = use_case.execute(timezone.localdate(), data.get('period_id'), data.get('months'))
        except AccountValidationError as exc:
            raise ValidationError(exc.errors) from exc
        return Response(serialize_income_expense(report))
