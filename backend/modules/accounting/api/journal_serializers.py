"""Serializadores del libro de asientos (CONT-11): validan forma y tipos; el negocio lo decide el dominio."""
from rest_framework import serializers

from modules.accounting.domain.journal import DESCRIPTION_MAX, MEMO_MAX, REASON_MAX, SOURCES
from modules.accounting.domain.posting import PostingNotFound, get_event

from .serializers import ORIGIN_MODULES

MONEY = {'max_digits': 12, 'decimal_places': 2, 'required': False, 'allow_null': True}


class JournalFiltersSerializer(serializers.Serializer):
    """Filtros (query params); un valor desconocido es un 400, nunca un listado vacío silencioso."""
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    account_id = serializers.UUIDField(required=False)
    source = serializers.ChoiceField(choices=SOURCES, required=False)
    origin_kind = serializers.CharField(max_length=30, required=False)

    def validate(self, attrs):
        if attrs.get('date_from') and attrs.get('date_to') and attrs['date_from'] > attrs['date_to']:
            raise serializers.ValidationError({'date_from': ['La fecha inicial no puede ser posterior a la final.']})
        return attrs


class JournalLineSerializer(serializers.Serializer):
    account_id = serializers.UUIDField()
    debit = serializers.DecimalField(**MONEY)
    credit = serializers.DecimalField(**MONEY)
    memo = serializers.CharField(max_length=MEMO_MAX, required=False, allow_blank=True, default='')


class JournalEntryInputSerializer(serializers.Serializer):
    """Alta manual: nunca acepta origen (los asientos automáticos los crean los módulos)."""
    accounting_date = serializers.DateField()
    description = serializers.CharField(max_length=DESCRIPTION_MAX)
    lines = JournalLineSerializer(many=True, allow_empty=False)


class JournalReverseSerializer(serializers.Serializer):
    reversal_date = serializers.DateField()
    reason = serializers.CharField(max_length=REASON_MAX)


def _origin(kind, origin_id, enabled, detail: bool):
    if origin_id is None:
        return None
    try:
        event = get_event(kind)  # los asientos automáticos llevan el código de su evento como origen
    except PostingNotFound:
        event = None
    module = event.module if event else ORIGIN_MODULES.get(kind)
    data = {'kind': kind, 'available': module in enabled}
    if event:
        data['label'] = event.label
        data['module'] = event.module
    if detail:
        data['id'] = str(origin_id)
    return data


def serialize_journal_row(model, enabled: frozenset[str]) -> dict:
    return {
        'id': str(model.id), 'accounting_date': model.accounting_date, 'description': model.description,
        'source': model.source, 'origin': _origin(model.origin_kind, model.origin_id, enabled, False),
        'currency': model.currency, 'total': str(model.total), 'created_by_name': model.created_by_name,
        'created_at': model.created_at, 'is_reversal': model.reverses_id is not None,
        'reversed_by_id': str(model.reversed_by_entry.id) if hasattr(model, 'reversed_by_entry') else None,
    }


def serialize_journal_detail(entry, accounts: dict, period, enabled: frozenset[str]) -> dict:
    def account(account_id):
        found = accounts.get(account_id)
        return {'id': str(account_id), 'code': found.code if found else None, 'name': found.name if found else ''}

    return {
        'id': str(entry.id), 'accounting_date': entry.accounting_date, 'description': entry.description,
        'source': entry.source, 'origin': _origin(entry.origin_kind, entry.origin_id, enabled, True),
        'currency': entry.currency, 'total': str(entry.total_debit),
        'total_debit': str(entry.total_debit), 'total_credit': str(entry.total_credit),
        'period': {'id': str(period.id), 'name': period.name} if period else None,
        'created_by_name': entry.created_by_name, 'created_at': entry.created_at,
        'lines': [{'position': line.position, 'account': account(line.account_id), 'debit': str(line.debit),
                   'credit': str(line.credit), 'memo': line.memo} for line in entry.lines],
        'is_reversal': entry.is_reversal,
        'reverses_id': str(entry.reverses_id) if entry.reverses_id else None,
        'reversed_by_id': str(entry.reversed_by_id) if entry.reversed_by_id else None,
        'reversal_reason': entry.reversal_reason,
        'can_reverse': not entry.is_reversal and entry.reversed_by_id is None,
    }
