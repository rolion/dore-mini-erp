from decimal import Decimal

from rest_framework import serializers

from modules.accounting.domain.account import NAME_MAX_LENGTH
from modules.accounting.domain.catalog import METHOD_CODES, METHOD_LABELS, ORIGIN_KINDS, ORIGIN_LABELS


class AccountInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=NAME_MAX_LENGTH, trim_whitespace=False)
    currency = serializers.CharField(max_length=3)


class AccountUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=NAME_MAX_LENGTH, trim_whitespace=False, required=False)
    currency = serializers.CharField(max_length=3, required=False)


class MethodInputSerializer(serializers.Serializer):
    account_id = serializers.UUIDField(allow_null=True)
    is_active = serializers.BooleanField(default=True)


def serialize_account(account) -> dict:
    return {'id': str(account.id), 'name': account.name, 'currency': account.currency,
            'is_active': account.is_active, 'created_at': account.created_at, 'updated_at': account.updated_at}


def serialize_method(view) -> dict:
    account = view.account
    return {
        'code': view.code, 'label': view.label, 'is_active': view.is_active,
        'account': ({'id': str(account.id), 'name': account.name, 'currency': account.currency,
                     'is_active': account.is_active} if account else None),
    }


class EntryFiltersSerializer(serializers.Serializer):
    """Filtros del libro (query params); un valor desconocido es un 400, nunca un listado vacío silencioso."""
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    account_id = serializers.UUIDField(required=False)
    method = serializers.ChoiceField(choices=METHOD_CODES, required=False)
    origin = serializers.ChoiceField(choices=ORIGIN_KINDS, required=False)

    def validate(self, attrs):
        if attrs.get('date_from') and attrs.get('date_to') and attrs['date_from'] > attrs['date_to']:
            raise serializers.ValidationError({'date_from': ['La fecha inicial no puede ser posterior a la final.']})
        return attrs


# Módulo propietario de cada origen: solo si está habilitado se ofrece el enlace al documento.
ORIGIN_MODULES = {'PRODUCT': 'sales', 'SERVICE': 'receivables'}


def serialize_entry(row, enabled: frozenset[str], *, detail: bool = False) -> dict:
    data = {
        'id': str(row.id),
        'account': {'id': str(row.account_id), 'name': row.account.name, 'currency': row.account.currency},
        'currency': row.currency,
        'amount': str(row.amount),
        'payment_date': row.payment_date,
        'created_at': row.created_at,
        'method': row.payment_method,
        'method_label': METHOD_LABELS.get(row.payment_method, row.payment_method),
        'recorded_by_name': row.recorded_by_name,
        'origin': {'kind': row.origin_kind, 'label': ORIGIN_LABELS.get(row.origin_kind, row.origin_kind)},
        'source': {
            'document_ref': row.origin_document_ref,
            'receipt_number': row.receipt_number,
            'available': ORIGIN_MODULES.get(row.origin_kind) in enabled,
        },
    }
    if detail:
        data['source']['id'] = str(row.origin_id)
    return data


def serialize_totals(totals) -> list[dict]:
    return [{'currency': t.currency, 'count': t.count, 'amount': str(t.amount),
             'by_origin': {kind: str(t.by_origin.get(kind, Decimal('0.00'))) for kind in ORIGIN_KINDS}} for t in totals]


def serialize_coverage(coverage) -> dict:
    return {'first_payment_date': coverage.first_payment_date, 'last_payment_date': coverage.last_payment_date,
            'first_recorded_at': coverage.first_recorded_at}
