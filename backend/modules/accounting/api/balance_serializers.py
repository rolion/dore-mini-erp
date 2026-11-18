"""Serializadores de sumas y saldos (CONT-04): validan forma y tipos; el cálculo lo hace el dominio."""
from rest_framework import serializers

from modules.accounting.application.trial_balance import TrialBalance

MONEY_FIELDS = ('opening_debit_balance', 'opening_credit_balance', 'debit', 'credit', 'debit_balance',
                'credit_balance')


class BalanceFiltersSerializer(serializers.Serializer):
    """Filtros (query params); un valor desconocido es un 400, nunca una lista vacía silenciosa."""
    period_id = serializers.UUIDField(required=False)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    account_class = serializers.CharField(max_length=10, required=False)
    account_id = serializers.UUIDField(required=False)


def serialize_balances(result: TrialBalance) -> dict:
    rows = [{'account_id': str(row.account_id), 'code': row.code, 'name': row.name,
             'account_class': row.account_class, 'is_active': row.is_active,
             **{name: str(getattr(row, name)) for name in MONEY_FIELDS}} for row in result.rows]
    totals = {name: str(getattr(result.totals, name)) for name in MONEY_FIELDS}
    totals['balanced'] = result.totals.balanced
    return {'date_from': result.date_from, 'date_to': result.date_to, 'has_opening': result.date_from is not None,
            'rows': rows, 'totals': totals}
