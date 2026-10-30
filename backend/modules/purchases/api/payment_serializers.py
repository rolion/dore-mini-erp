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
    """Convierte `YYYY-MM-DD` en fecha; cualquier otro valor pasa intacto y lo rechaza el dominio como fecha inválida."""

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


def payment_representation(payment) -> dict:
    return {
        'id': payment.id,
        'reference': payment.reference,
        'amount': money(payment.amount),
        'payment_method': payment.payment_method.value,
        'payment_date': payment.payment_date.isoformat(),
        'status': payment.status.value,
        'user_name': payment.user_name,
        'created_at': payment.created_at,
    }
