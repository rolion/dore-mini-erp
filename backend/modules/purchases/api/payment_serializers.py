import datetime

from rest_framework import serializers

from .purchase_serializers import money


class RawField(serializers.Field):
    """Deja pasar el valor tal cual: el dominio valida tipo y regla de `amount` y `payment_method`.

    Así los errores de estos campos se devuelven juntos en una sola respuesta, en vez de que un error de forma
    oculte los de dominio.
    """

    def to_internal_value(self, data):
        return data

    def to_representation(self, value):
        return value


class LenientDateField(serializers.Field):
    """Convierte `YYYY-MM-DD` en fecha; otro valor pasa intacto y lo rechaza el dominio como fecha inválida."""

    def to_internal_value(self, data):
        if isinstance(data, str):
            try:
                return datetime.date.fromisoformat(data.strip())
            except ValueError:
                return data
        return data

    def to_representation(self, value):
        return value


class PaymentInputSerializer(serializers.Serializer):
    """Valida solo la identidad (`payment_id`); las reglas de monto, método y fecha las aplica el dominio."""

    payment_id = serializers.UUIDField()
    amount = RawField(required=False, allow_null=True)
    payment_method = RawField(required=False, allow_null=True)
    payment_date = LenientDateField(required=False, allow_null=True)


class PaymentPreviewQuerySerializer(serializers.Serializer):
    """Mismos campos y tolerancia que el alta: las reglas las aplica el dominio."""

    amount = RawField(required=False, allow_null=True)
    payment_method = RawField(required=False, allow_null=True)
    payment_date = LenientDateField(required=False, allow_null=True)


def preview_representation(preview) -> dict:
    return {
        'covered': preview.covered,
        'debt_amount': money(preview.debt_amount),
        'advance_amount': money(preview.advance_amount),
        'lines': [{'side': line.side, 'role': line.role, 'account': {'name': line.account_name},
                   'amount': money(line.amount)} for line in preview.lines],
        'issues': list(preview.issues),
    }


def payment_representation(payment, classifications: dict | None = None, entries=()) -> dict:
    info = (classifications or {}).get(payment.classification_id) if payment.classification_id else None
    return {
        'id': payment.id,
        'reference': payment.reference,
        'amount': money(payment.amount),
        'payment_method': payment.payment_method.value,
        'payment_date': payment.payment_date.isoformat(),
        'status': payment.status.value,
        'classification': (None if payment.classification_id is None else
                           {'id': payment.classification_id, 'name': info.name if info else '',
                            'active': info.active if info else False}),
        'user_name': payment.user_name,
        'created_at': payment.created_at,
        'debt_amount': money(payment.debt_amount),
        'advance_amount': money(payment.advance_amount),
        'accounting_entries': [{'id': e.id, 'kind': e.kind, 'accounting_date': e.accounting_date.isoformat(),
                                'total': money(e.total)} for e in entries],
    }


class PaymentClassificationInputSerializer(serializers.Serializer):
    classification_id = serializers.UUIDField(allow_null=True)
