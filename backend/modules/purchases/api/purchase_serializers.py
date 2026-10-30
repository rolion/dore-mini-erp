from rest_framework import serializers

from modules.purchases.domain.purchase import CURRENCY


class DecimalInputField(serializers.Field):
    """Acepta un decimal como texto o un entero JSON; nunca float. El dominio valida el valor."""

    def to_internal_value(self, data):
        if isinstance(data, bool) or not isinstance(data, (str, int)):
            raise serializers.ValidationError('Debe ser un número decimal enviado como texto.')
        return data

    def to_representation(self, value):
        return value


class PurchaseItemInputSerializer(serializers.Serializer):
    """Valida forma y tipos; `subtotal`, `product_name` y demás campos desconocidos se ignoran."""

    product_id = serializers.UUIDField()
    quantity = DecimalInputField()
    unit_price = DecimalInputField()


class PurchaseInputSerializer(serializers.Serializer):
    """Valida forma y tipos; las reglas las aplican el dominio y la aplicación.

    `total`, `status`, descuentos e impuestos no existen: si llegan, se ignoran.
    """

    supplier_id = serializers.UUIDField(required=False, allow_null=True)
    purchase_date = serializers.DateField(required=False, allow_null=True)
    external_reference = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    items = PurchaseItemInputSerializer(many=True, required=False)


class CancelPurchaseSerializer(serializers.Serializer):
    """Valida forma y tipos; la regla del motivo (obligatorio, ≤ 500) la aplica el dominio."""

    reason = serializers.CharField(allow_blank=True, allow_null=True, required=False)


def money(value) -> str:
    return f'{value:.2f}'


def quantity(value) -> str:
    return f'{value:.3f}'


def purchase_representation(detail) -> dict:
    purchase, supplier = detail.purchase, detail.supplier
    return {
        'id': purchase.id,
        'supplier': {
            'id': purchase.supplier_id,
            'name': supplier.name if supplier else '',
            'active': supplier.active if supplier else False,
        },
        'purchase_date': purchase.purchase_date.isoformat(),
        'external_reference': purchase.external_reference,
        'notes': purchase.notes,
        'status': purchase.status.value,
        'currency': CURRENCY,
        'editable': purchase.editable,
        'reference': purchase.reference,
        'reception_status': purchase.reception_status.value,
        'payment_status': purchase.payment_status.value,
        'confirmed_at': purchase.confirmed_at,
        'cancelled_at': purchase.cancelled_at,
        'cancellation_reason': purchase.cancellation_reason,
        'allowed_actions': purchase.allowed_actions,
        'items': [{
            'id': item.id,
            'product_id': item.product_id,
            'product_name': item.product_name,
            'unit_abbreviation': item.unit_abbreviation,
            'quantity': quantity(item.quantity),
            'unit_price': money(item.unit_price),
            'subtotal': money(item.subtotal),
        } for item in purchase.items],
        'total': money(purchase.total),
        'created_at': purchase.created_at,
        'updated_at': purchase.updated_at,
    }


def summary_representation(summary) -> dict:
    return {
        'id': summary.id,
        'purchase_date': summary.purchase_date.isoformat(),
        'supplier': {'id': summary.supplier_id, 'name': summary.supplier_name},
        'external_reference': summary.external_reference,
        'total': money(summary.total),
        'currency': CURRENCY,
        'status': summary.status.value,
        'items_count': summary.items_count,
    }
