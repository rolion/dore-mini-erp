"""API de sumas y saldos por cuenta (CONT-04): solo lectura sobre el libro de asientos."""
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.accounting.application.trial_balance import GetTrialBalance, TrialBalanceFilters
from modules.accounting.domain.account import AccountValidationError
from modules.accounting.infrastructure.django.repositories import (
    DjangoAccountRepository,
    DjangoFiscalPeriodRepository,
    DjangoJournalRepository,
)
from shared.tenancy import company_id_from

from .balance_serializers import BalanceFiltersSerializer, serialize_balances


class BalanceListView(APIView):
    required_modules = ('accounting',)

    def get(self, request):
        company_id = company_id_from(request)
        serializer = BalanceFiltersSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        use_case = GetTrialBalance(DjangoAccountRepository(company_id), DjangoJournalRepository(company_id),
                                   DjangoFiscalPeriodRepository(company_id))
        try:
            result = use_case.execute(TrialBalanceFilters(**serializer.validated_data))
        except AccountValidationError as exc:
            raise ValidationError(exc.errors) from exc
        return Response(serialize_balances(result))
