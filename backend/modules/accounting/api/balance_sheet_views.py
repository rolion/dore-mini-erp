"""API del balance general: solo lectura sobre el libro de asientos."""
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.accounting.application.balance_sheet import BalanceSheetFilters, GetBalanceSheet
from modules.accounting.domain.account import AccountValidationError
from modules.accounting.infrastructure.django.repositories import DjangoAccountRepository, DjangoJournalRepository
from shared.tenancy import company_id_from

from .balance_sheet_serializers import BalanceSheetFiltersSerializer, serialize_balance_sheet


class BalanceSheetView(APIView):
    required_modules = ('accounting',)

    def get(self, request):
        company_id = company_id_from(request)
        serializer = BalanceSheetFiltersSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        use_case = GetBalanceSheet(DjangoAccountRepository(company_id), DjangoJournalRepository(company_id))
        try:
            report = use_case.execute(BalanceSheetFilters(**serializer.validated_data))
        except AccountValidationError as exc:
            raise ValidationError(exc.errors) from exc
        return Response(serialize_balance_sheet(report))
