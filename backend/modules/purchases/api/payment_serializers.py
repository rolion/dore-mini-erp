from rest_framework import serializers

from .purchase_serializers import DecimalInputField, money


class PaymentInputSerializer(serializers.Serializer):
    """Valida forma y tipos; las reglas (monto, saldo, método, fecha) las aplica el dominio."""

    payment_id = serializers.UUIDField()
    amount = DecimalInputField(required=False, allow_null=True)
    payment_method = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    payment_date = serializers.DateField(required=False, allow_null=True)


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
