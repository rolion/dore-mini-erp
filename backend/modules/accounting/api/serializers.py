from decimal import Decimal

from rest_framework import serializers

from modules.accounting.domain.account import NAME_MAX_LENGTH
from modules.accounting.domain.catalog import (
    DIRECTIONS,
    ENTRY_ORIGIN_KINDS,
    ENTRY_ORIGIN_LABELS,
    METHOD_CODES,
    METHOD_LABELS,
    ORIGIN_KINDS,
)


class AccountInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=NAME_MAX_LENGTH, trim_whitespace=False)
    currency = serializers.CharField(max_length=3)
    # El dominio valida formato; `code` y `account_class` son obligatorios al crear (lo exige el caso de uso).
    code = serializers.CharField(max_length=64, required=False, allow_null=True)
    account_class = serializers.CharField(max_length=10, required=False, allow_null=True)
    kind = serializers.CharField(max_length=10, required=False, allow_null=True)  # solo cuentas de dinero (Activo)
    is_contra = serializers.BooleanField(required=False)
    opening_balance = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)


class AccountUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=NAME_MAX_LENGTH, trim_whitespace=False, required=False)
    currency = serializers.CharField(max_length=3, required=False)
    code = serializers.CharField(max_length=64, required=False, allow_null=True)
    kind = serializers.CharField(max_length=10, required=False, allow_null=True)
    account_class = serializers.CharField(max_length=10, required=False, allow_null=True)
    is_contra = serializers.BooleanField(required=False)
    opening_balance = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)


class ClassificationInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=NAME_MAX_LENGTH, trim_whitespace=False)
    direction = serializers.CharField(max_length=10)


class ClassificationUpdateSerializer(serializers.Serializer):
    """Solo el nombre: la dirección es inmutable (cualquier otro campo se rechaza)."""
    name = serializers.CharField(max_length=NAME_MAX_LENGTH, trim_whitespace=False)

    def to_internal_value(self, data):
        extra = set(data) - set(self.fields)
        if extra:
            raise serializers.ValidationError({field: ['Este campo no se puede modificar.'] for field in extra})
        return super().to_internal_value(data)


def serialize_classification(classification) -> dict:
    return {'id': str(classification.id), 'name': classification.name, 'direction': classification.direction,
            'is_active': classification.is_active, 'created_at': classification.created_at,
            'updated_at': classification.updated_at}


class RegularizationInputSerializer(serializers.Serializer):
    """Periodo y mapeo histórico explícito. La empresa nunca viene en el cuerpo: sale de la sesión."""
    date_from = serializers.DateField(required=False, allow_null=True, default=None)
    date_to = serializers.DateField(required=False, allow_null=True, default=None)
    mapping = serializers.DictField(child=serializers.ListField(child=serializers.DictField()), allow_empty=True)

    def validate(self, attrs):
        if attrs['date_from'] and attrs['date_to'] and attrs['date_from'] > attrs['date_to']:
            raise serializers.ValidationError({'date_from': ['La fecha inicial no puede ser posterior a la final.']})
        return attrs


class RegularizationApplySerializer(RegularizationInputSerializer):
    confirm = serializers.BooleanField(default=False)

    def validate_confirm(self, value):
        if value is not True:
            raise serializers.ValidationError('Confirma la regularización con confirm: true.')
        return value


class MethodInputSerializer(serializers.Serializer):
    account_id = serializers.UUIDField(allow_null=True)
    is_active = serializers.BooleanField(default=True)


def serialize_account(account, has_entries: bool = False) -> dict:
    return {'id': str(account.id), 'name': account.name, 'currency': account.currency, 'kind': account.kind,
            'code': account.code, 'is_contra': account.is_contra, 'account_class': account.account_class,
            'has_entries': has_entries, 'opening_balance': str(account.opening_balance),
            'is_active': account.is_active,
            'created_at': account.created_at, 'updated_at': account.updated_at}


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
    origin = serializers.ChoiceField(choices=ENTRY_ORIGIN_KINDS, required=False)
    direction = serializers.ChoiceField(choices=DIRECTIONS, required=False)

    def validate(self, attrs):
        if attrs.get('date_from') and attrs.get('date_to') and attrs['date_from'] > attrs['date_to']:
            raise serializers.ValidationError({'date_from': ['La fecha inicial no puede ser posterior a la final.']})
        return attrs


# Módulo propietario de cada origen: solo si está habilitado se ofrece el enlace al documento.
ORIGIN_MODULES = {'PRODUCT': 'sales', 'SERVICE': 'receivables', 'EXPENSE': 'expenses', 'PURCHASE_PAYMENT': 'purchases'}


def serialize_entry(row, enabled: frozenset[str], classifications: dict | None = None, *, detail: bool = False) -> dict:
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
        'origin': {'kind': row.origin_kind, 'label': ENTRY_ORIGIN_LABELS.get(row.origin_kind, row.origin_kind)},
        'direction': row.direction,
        'operation': row.operation,
        'classification': ({'id': str(row.classification_id),
                            'name': (classifications or {}).get(row.classification_id, '')}
                           if row.classification_id else None),
        'reversal_of': str(row.reverses_id) if row.reverses_id else None,
        'reversed_by': str(row.reversed_by_entry.id) if hasattr(row, 'reversed_by_entry') else None,
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
    """`amount` y `by_origin` son los ingresos (compatibles con la API anterior); `by_direction` añade el resto."""
    return [{'currency': t.currency, 'count': t.count, 'amount': str(t.amount),
             'by_origin': {kind: str(t.by_origin.get(kind, Decimal('0.00'))) for kind in ORIGIN_KINDS},
             'expense': str(t.expense),
             'by_direction': {'income': str(t.amount), 'expense': str(t.expense),
                              'reversed_income': str(t.reversed_income), 'reversed_expense': str(t.reversed_expense),
                              'net': str(t.net)}} for t in totals]


def serialize_gaps(gaps) -> list[dict]:
    return [{'from': gap.from_on, 'to': gap.to_on} for gap in gaps]


def serialize_coverage(coverage, settings=None) -> dict:
    data = {'first_payment_date': coverage.first_payment_date, 'last_payment_date': coverage.last_payment_date,
            'first_recorded_at': coverage.first_recorded_at}
    if settings is not None:
        data.update({'cutoff_date': settings.cutoff_date, 'gaps': serialize_gaps(settings.gaps)})
    return data


class SettingsUpdateSerializer(serializers.Serializer):
    cutoff_date = serializers.DateField()


def serialize_settings(view) -> dict:
    return {'cutoff_date': view.cutoff_date, 'enabled_at': view.enabled_at, 'locked': view.locked,
            'gaps': serialize_gaps(view.gaps)}


def serialize_account_class(view) -> dict:
    return {'code': view.code, 'enabled': view.enabled}


class FiscalPeriodInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=NAME_MAX_LENGTH, trim_whitespace=False)
    start_date = serializers.DateField()
    end_date = serializers.DateField()


class FiscalPeriodUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=NAME_MAX_LENGTH, trim_whitespace=False, required=False)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)


def serialize_fiscal_period(period) -> dict:
    return {'id': str(period.id), 'name': period.name, 'start_date': period.start_date, 'end_date': period.end_date,
            'status': period.status, 'closed_at': period.closed_at, 'closed_by_name': period.closed_by_name,
            'reopened_at': period.reopened_at, 'reopened_by_name': period.reopened_by_name,
            'created_at': period.created_at, 'updated_at': period.updated_at}
