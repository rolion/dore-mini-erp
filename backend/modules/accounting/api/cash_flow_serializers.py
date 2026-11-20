from rest_framework import serializers

from .journal_serializers import _origin

MOVEMENT_TYPES = ('inflow', 'outflow', 'transfer')


class CashFlowRangeSerializer(serializers.Serializer):
    """Rango de fechas contables obligatorio (query params)."""
    date_from = serializers.DateField()
    date_to = serializers.DateField()

    def validate(self, attrs):
        if attrs['date_from'] > attrs['date_to']:
            raise serializers.ValidationError({'date_from': ['La fecha inicial no puede ser posterior a la final.']})
        return attrs


class CashFlowMovementsFiltersSerializer(CashFlowRangeSerializer):
    account_id = serializers.UUIDField(required=False)
    type = serializers.ChoiceField(choices=MOVEMENT_TYPES, required=False)


def _money(value) -> str:
    return f'{value:.2f}'


def serialize_cash_flow(report) -> dict:
    flow = report.cash_flow
    return {
        'coverage': {'cutoff_date': report.cutoff_date, 'partial': report.partial},
        'summary': {'opening': _money(flow.opening), 'inflow': _money(flow.inflow), 'outflow': _money(flow.outflow),
                    'net': _money(flow.net), 'closing': _money(flow.closing), 'transfers': _money(flow.transfers)},
        'accounts': [{'account_id': str(a.account_id), 'name': a.name, 'opening': _money(a.opening),
                      'inflow': _money(a.inflow), 'outflow': _money(a.outflow),
                      'transfers_in': _money(a.transfers_in), 'transfers_out': _money(a.transfers_out),
                      'net': _money(a.net), 'closing': _money(a.closing)} for a in flow.accounts],
    }


def serialize_movement(movement, enabled: frozenset[str]) -> dict:
    return {
        'entry_id': str(movement.entry_id), 'accounting_date': movement.accounting_date,
        'account': {'id': str(movement.account_id), 'name': movement.account_name},
        'description': movement.description,
        'origin': _origin(movement.origin_kind, movement.origin_id, enabled, True),
        'kind': movement.kind, 'amount': _money(movement.amount), 'is_reversal': movement.is_reversal,
    }


def serialize_movement_totals(result) -> dict:
    return {'inflow': _money(result.inflow), 'outflow': _money(result.outflow),
            'transfers_in': _money(result.transfers_in), 'transfers_out': _money(result.transfers_out)}
